"""Free, offline attendance-sheet reader (no API key, no internet).

How it works on the printed BELTEI-style sheet:

1. RapidOCR reads the printed text and its position: student IDs, Latin names, M/F,
   the header (major, program, year, semester, week, room), the column dates and
   subject codes. OCR often drops the space in a name ("CHEASEREYBOTH"); it is put back
   from a closer re-read of the name, or else from the widest blank gap between letters.
   Khmer names are read with Tesseract's Khmer model when it is installed.
2. Each student row is located from its ID (and M/F box); the mark area lies between
   the gender column and the "Batch" column.
3. Vertical grid lines inside the mark area give the cells. Merged or grey shaded
   columns (no class) are skipped.
4. Each cell is classified by ink colour: red ink -> "P" (0), dark/blue ink -> tick (1),
   no ink -> blank. Borderline cells become "?" so they are reported, not guessed.

The result is the same `ExtractedSheet` the Claude reader returns, so saving is shared.
"""

import difflib
import logging
import os
import re
import shutil
import statistics
import subprocess
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from app.core.config import get_settings
from app.core.errors import AppError
from app.services.sheet_reader import ExtractedColumn, ExtractedSheet, ExtractedStudent

logger = logging.getLogger("app.offline_reader")

MAX_EDGE = 1600            # px; larger photos are downscaled before OCR
RED_P_RATIO = 0.006        # share of red pixels in a cell that means "P"
INK_TICK_RATIO = 0.04      # share of ink pixels that means a tick
INK_UNSURE_RATIO = 0.02    # between this and INK_TICK_RATIO the cell is reported as "?"
DOT_EXTENT = 0.3           # ink shorter than this share of the cell height is a dot, not a tick

ID_RE = re.compile(r"\d{6,10}")  # e.g. 00058285 or 057017 (sheets differ)
DATE_RE = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})")


@lru_cache
def _ocr_engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def _boxes(image: np.ndarray) -> list[dict]:
    result, _ = _ocr_engine()(image)
    boxes = []
    for box, text, conf in result or []:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        boxes.append({"t": text.strip(), "c": float(conf), "x0": min(xs), "x1": max(xs),
                      "y0": min(ys), "y1": max(ys)})
    return boxes


def _cx(b): return (b["x0"] + b["x1"]) / 2
def _cy(b): return (b["y0"] + b["y1"]) / 2


def _decode(data: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise AppError("The file is not a readable image (use JPG, PNG or WebP).", code="invalid_image")
    scale = MAX_EDGE / max(image.shape[:2])
    if scale < 1:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return image


def _deskew(image: np.ndarray, ids: list[dict]) -> np.ndarray | None:
    """Rotate so the student-ID column is vertical; None if already straight."""
    if len(ids) < 5:
        return None
    ys = np.array([_cy(b) for b in ids])
    xs = np.array([_cx(b) for b in ids])
    slope = np.polyfit(ys, xs, 1)[0]
    angle = float(np.degrees(np.arctan(slope)))
    if abs(angle) < 0.4:
        return None
    h, w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), -angle, 1.0)
    return cv2.warpAffine(image, matrix, (w, h), borderMode=cv2.BORDER_REPLICATE)


# --------------------------------------------------------------------------- header


def _header(boxes: list[dict]) -> dict:
    text = "\n".join(b["t"] for b in sorted(boxes, key=lambda b: (_cy(b), b["x0"])))

    def find(pattern, cast=str):
        # [ \t]* rather than \s*: a value must be on its own label's line, never borrowed from the next.
        m = re.search(pattern.replace(r"\s*", r"[ \t]*"), text, flags=re.IGNORECASE)
        return cast(m.group(1).strip()) if m else None

    def words(value):
        # OCR drops spaces: "EnglishIntensive Course" -> "English Intensive Course"
        return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value) if value else value

    # OCR often reads the Roman "II" as "Il", "ll" or "11".
    semester = find(r"Semester\s*:?\s*([IVl1|2]{1,2})\b")
    semester = re.sub(r"[l1|]", "I", semester or "").upper()
    semester = {"I": 1, "II": 2, "2": 2}.get(semester)
    return {
        "faculty": words(find(r"Faculty\s*:\s*([^\n]+)")),
        "program": find(r"Program\s*:\s*([A-Za-z0-9 ]+)"),
        "major": words(find(r"Major\s*:\s*([^\n]+)")),
        "academic_year": find(r"Year\s*:\s*(\d{1,2})\b", int),
        "semester": semester,
        "week": find(r"Week\s*:?\s*(\d{1,2})\b", int),
        "room": find(r"Room\s*:\s*([A-Za-z0-9-]+)"),
    }


def _legend(boxes: list[dict]) -> dict[str, str]:
    """'APP II = Advanced Python Programming II' -> {'APPII': 'Advanced Python Programming II'}."""
    legend = {}
    for b in boxes:
        if "=" in b["t"]:
            code, _, name = b["t"].partition("=")
            if code.strip() and name.strip():
                # OCR drops spaces: "AdvancedPythonProgramming" -> "Advanced Python Programming"
                name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name.strip())
                legend[re.sub(r"\s+", "", code).upper()] = name
    return legend


def _legend_name(legend: dict[str, str], code: str) -> str | None:
    match = difflib.get_close_matches(code, legend.keys(), n=1, cutoff=0.75)
    return legend[match[0]] if match else None


# --------------------------------------------------------------------------- names


def _split_points(letters: str, reading: str) -> set[int]:
    """Where `reading` has spaces, as positions in `letters` (re-reads may drop a letter)."""
    points, compact = set(), []
    for ch in reading:
        if ch == " ":
            points.add(len(compact))
        else:
            compact.append(ch)
    matcher = difflib.SequenceMatcher(None, "".join(compact), letters, autojunk=False)
    if matcher.ratio() < 0.8:
        return set()
    mapped = set()
    for point in points:
        for a, b, size in matcher.get_matching_blocks():
            if a <= point <= a + size:
                mapped.add(b + point - a)
                break
    return {p for p in mapped if 0 < p < len(letters)}


def _widest_gap(gray: np.ndarray, box: dict, letters: str) -> int | None:
    """Letter position of the widest blank column run inside the name box."""
    x0, x1, y0, y1 = int(box["x0"]), int(box["x1"]), int(box["y0"]), int(box["y1"])
    crop = gray[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    _, bw = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    blank = (bw > 0).sum(axis=0) == 0
    best, start = (0, 0), None
    for i, empty in enumerate([*blank, False]):
        if empty and start is None:
            start = i
        elif not empty and start is not None:
            if start > 0 and i < len(blank) and i - start > best[1]:
                best = (start, i - start)
            start = None
    if best[1] < max(2, (y1 - y0) * 0.12):
        return None
    point = round((best[0] + best[1] / 2) / (x1 - x0) * len(letters))
    return point if 0 < point < len(letters) else None


def _reread(image: np.ndarray, x0: int, x1: int, y0: int, y1: int, scale: int) -> str:
    """Recognise one text line again from an enlarged crop (small print reads better)."""
    crop = image[max(0, y0):y1, max(0, x0):x1]
    if crop.size == 0:
        return ""
    big = cv2.copyMakeBorder(cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC),
                             10, 10, 10, 10, cv2.BORDER_REPLICATE)
    result, _ = _ocr_engine()(big, use_det=False, use_cls=False, use_rec=True)
    return result[0][0].strip() if result else ""


def _check_ids(image: np.ndarray, boxes: list[dict], ids: list[dict], x_left: int, row_h: float) -> list[dict]:
    """Re-read every ID close up, and look for the ID of rows that have a name but no ID box."""
    ix0 = int(statistics.median(b["x0"] for b in ids)) - 4
    ix1 = int(statistics.median(b["x1"] for b in ids)) + 6

    def read(yc: float) -> str | None:
        y0, y1 = int(yc - row_h * 0.45), int(yc + row_h * 0.45)
        texts = {re.sub(r"\D", "", _reread(image, ix0, ix1, y0, y1, scale)) for scale in (2, 3)}
        # Only trust a re-read when both sizes agree on a whole ID.
        return texts.pop() if len(texts) == 1 and ID_RE.fullmatch(next(iter(texts))) else None

    # A re-read may drop a repeated digit, so it must have the usual ID length on this sheet.
    usual = statistics.mode(len(b["t"]) for b in ids)
    checked = []
    for b in ids:
        better = read(_cy(b))
        checked.append({**b, "t": better} if better and len(better) == usual and better != b["t"] else b)
    names = [n for n in boxes if ix1 < _cx(n) < x_left and re.fullmatch(r"[A-Z][A-Z .'-]{2,}", n["t"])
             and n["t"] not in ("M", "F")]
    for n in names:
        if not any(abs(_cy(b) - _cy(n)) < row_h / 2 for b in checked):
            found = read(_cy(n))
            if found and len(found) == usual:
                checked.append({"t": found, "c": 0.5, "x0": ix0, "x1": ix1, "y0": n["y0"], "y1": n["y1"]})
    return sorted(checked, key=_cy)


def _spaced_name(image: np.ndarray, gray: np.ndarray, box: dict) -> str:
    text = box["t"]
    if " " in text:
        return text
    x0, x1, y0, y1 = int(box["x0"]), int(box["x1"]), int(box["y0"]), int(box["y1"])
    crop = image[max(0, y0 - 3):y1 + 3, max(0, x0 - 4):x1 + 4]
    votes: dict[frozenset, int] = {}
    for scale in (3, 2):
        big = cv2.copyMakeBorder(cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC),
                                 10, 10, 10, 10, cv2.BORDER_REPLICATE)
        result, _ = _ocr_engine()(big, use_det=False, use_cls=False, use_rec=True)
        points = _split_points(text, result[0][0]) if result else set()
        if points:
            votes[frozenset(points)] = votes.get(frozenset(points), 0) + 1
    if votes:
        points = max(votes, key=votes.get)
    else:
        gap = _widest_gap(gray, box, text)
        points = {gap} if gap else set()
    return "".join(f" {ch}" if i in points else ch for i, ch in enumerate(text))


KHMER_RE = re.compile(r"[ក-៿᧠-᧿]+")


@lru_cache
def _tesseract() -> tuple[str, str | None] | None:
    """(tesseract executable, tessdata dir) when Khmer OCR is available, else None."""
    settings = get_settings()
    cmd = settings.tesseract_cmd or shutil.which("tesseract") or next(
        (str(p) for p in (Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR/tesseract.exe",
                          Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Tesseract-OCR/tesseract.exe")
         if p.is_file()), None)
    if not cmd:
        logger.info("Tesseract not found; Khmer names will be left blank.")
        return None
    candidates = [settings.tessdata_dir, os.environ.get("TESSDATA_PREFIX"),
                  str(Path(os.environ.get("LOCALAPPDATA", "")) / "tessdata"), str(Path(cmd).parent / "tessdata")]
    tessdata = next((d for d in candidates if d and (Path(d) / "khm.traineddata").is_file()), None)
    if tessdata is None:
        logger.info("khm.traineddata not found; Khmer names will be left blank.")
        return None
    return cmd, tessdata


def _tesseract_words(gray_crop: np.ndarray) -> list[tuple[str, float]]:
    cmd, tessdata = _tesseract()
    ok, png = cv2.imencode(".png", gray_crop)
    try:
        result = subprocess.run([cmd, "stdin", "stdout", "-l", "khm", "--psm", "7", "--tessdata-dir", tessdata,
                                 "-c", "tessedit_create_tsv=1"], input=png.tobytes(), capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        logger.warning("Tesseract failed on a Khmer name", exc_info=True)
        return []
    words = []
    for line in result.stdout.decode("utf-8", "replace").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) == 12 and parts[11].strip():
            words.append((parts[11].strip(), float(parts[10])))
    return words


def _khmer_name(gray: np.ndarray, x0: int, x1: int, y: float, row_h: float) -> str | None:
    """Read the Khmer name between the ID and the Latin name; junk from grid lines is dropped."""
    best, best_score = None, (0, 0.0)
    # A tighter crop is tried only when the first one did not give a family and a given name.
    for half in (0.45, 0.38):
        if best_score[0] >= 2:
            break
        crop = gray[max(0, int(y - row_h * half)):int(y + row_h * half), x0:x1]
        if crop.size == 0:
            return None
        for scale in (2, 3):
            big = cv2.copyMakeBorder(cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC),
                                     12, 12, 12, 12, cv2.BORDER_REPLICATE)
            words = []
            for text, conf in _tesseract_words(big):
                text = "".join(KHMER_RE.findall(text))
                # A lone letter or a weak extra word is a stray grid-line fragment, not part of the name.
                if len(text) > 1 and (len(words) < 2 or conf >= 70):
                    words.append((text, conf))
            if words:
                score = (min(len(words), 2), sum(c for _, c in words) / len(words))
                if score > best_score:
                    best, best_score = " ".join(w for w, _ in words), score
    return best


# --------------------------------------------------------------------------- grid 


def _vertical_lines(dark: np.ndarray, x0: int, x1: int, y0: int, y1: int, row_h: float) -> list[int]:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, int(row_h * 4))))
    # Widen strokes first so thin lines that lean a little (photo taken at an angle) stay unbroken.
    widened = cv2.dilate(dark[y0:y1, :], np.ones((1, 3), np.uint8))
    vertical = cv2.morphologyEx(widened, cv2.MORPH_OPEN, kernel)
    profile = vertical[:, x0:x1].sum(axis=0) / 255
    hits = [x0 + i for i, value in enumerate(profile) if value > (y1 - y0) * 0.3]
    groups: list[list[int]] = []
    for x in hits:
        if groups and x - groups[-1][-1] <= 2:
            groups[-1].append(x)
        else:
            groups.append([x])
    return [int(np.mean(g)) for g in groups]


def read_sheet_offline(data: bytes) -> ExtractedSheet:
    image = _decode(data)
    boxes = _boxes(image)
    ids = [b for b in boxes if ID_RE.fullmatch(b["t"])]
    straight = _deskew(image, ids)
    if straight is not None:
        image, boxes = straight, _boxes(straight)
        ids = [b for b in boxes if ID_RE.fullmatch(b["t"])]

    if len(ids) < 1:
        raise AppError("No student IDs could be read. Take the photo straight on, in good light, "
                       "with the whole sheet visible.", code="scan_no_students")
    ids.sort(key=_cy)

    genders = [b for b in boxes if b["t"] in ("M", "F")]
    batch = [b for b in boxes if "(1st" in b["t"] or "(2nd" in b["t"] or b["t"].lower() == "batch"]
    dates = sorted([b for b in boxes if DATE_RE.fullmatch(b["t"])], key=_cx)
    if not genders or not dates:
        raise AppError("Could not find the gender and date columns. Is this a weekly attendance sheet?",
                       code="scan_layout_unknown")

    row_h = float(statistics.median(np.diff([_cy(b) for b in ids]))) if len(ids) > 1 else 20.0
    x_left = int(max(b["x1"] for b in genders)) + 2
    ids = _check_ids(image, boxes, ids, x_left, row_h)
    x_right = int(min(b["x0"] for b in batch)) - 2 if batch else int(max(b["x1"] for b in dates)) + 5
    y_top = max(0, int(_cy(ids[0]) - row_h))
    y_bot = min(image.shape[0], int(_cy(ids[-1]) + row_h))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    dark = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 12)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    lines = _vertical_lines(dark, x_left, x_right + 3, y_top, y_bot, row_h)
    cells = [(a, b) for a, b in zip(lines, lines[1:]) if b - a > 6]
    if not cells:
        raise AppError("Could not find the attendance grid. Take the photo straight on.",
                       code="scan_layout_unknown")
    typical = statistics.median(b - a for a, b in cells)

    # Masks: grid lines are excluded from ink; red ink is a "P".
    k = max(8, int(row_h * 3))
    grid = cv2.bitwise_or(
        cv2.morphologyEx(dark, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, 1))),
        cv2.morphologyEx(dark, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, k))),
    )
    grid = cv2.dilate(grid, np.ones((3, 3), np.uint8)) > 0
    red = ((h <= 12) | (h >= 160)) & (s > 50) & (v > 40)
    ink = (dark > 0) & ~grid & ~red

    # Rows: centre on the M/F box when there is one (it sits right next to the marks).
    rows = []
    for b in ids:
        yc = _cy(b)
        near = [g for g in genders if abs(_cy(g) - yc) < row_h / 2]
        gender = min(near, key=lambda g: abs(_cy(g) - yc)) if near else None
        names = [n for n in boxes if abs(_cy(n) - yc) < row_h / 2 and b["x1"] < _cx(n) < x_left
                 and re.fullmatch(r"[A-Z][A-Z .'-]{2,}", n["t"]) and n["t"] not in ("M", "F")]
        name = _spaced_name(image, gray, max(names, key=lambda n: n["x1"] - n["x0"])) if names else ""
        latin_x0 = int(min(n["x0"] for n in names)) if names else int(b["x1"] + (x_left - b["x1"]) / 2)
        rows.append({"id": b["t"], "y": _cy(gender) if gender else yc, "id_y": yc,
                     "gender": gender["t"] if gender else None, "name": name,
                     "khmer_span": (int(b["x1"]) + 6, latin_x0 - 6)})

    khmer = [None] * len(rows)
    if _tesseract():
        with ThreadPoolExecutor(max_workers=4) as pool:
            khmer = list(pool.map(lambda r: _khmer_name(gray, *r["khmer_span"], r["id_y"], row_h), rows))

    # Classify every cell, then decide which columns are real class sessions.
    y_half = row_h * 0.32
    readings = []  # per column: list of (red_ratio, ink_ratio, mean_v, ink_extent)
    for a, b in cells:
        margin = int((b - a) * 0.18)
        column = []
        for row in rows:
            ys = slice(int(row["y"] - y_half), int(row["y"] + y_half))
            xs = slice(a + margin, b - margin)
            area = max(1, (ys.stop - ys.start) * (xs.stop - xs.start))
            inked = np.flatnonzero(ink[ys, xs].any(axis=1))
            extent = (inked[-1] - inked[0] + 1) / (ys.stop - ys.start) if inked.size else 0.0
            column.append((red[ys, xs].sum() / area, ink[ys, xs].sum() / area, float(v[ys, xs].mean()), extent))
        readings.append(column)

    col_v = [statistics.median(r[2] for r in col) for col in readings]
    overall_v = statistics.median(col_v)

    columns: list[ExtractedColumn] = []
    kept: list[int] = []
    legend = _legend(boxes)
    date_y = max(_cy(d) for d in dates)
    subjects = [b for b in boxes if date_y + 4 < _cy(b) < _cy(ids[0]) - row_h / 2
                and re.fullmatch(r"[A-Za-z][A-Za-z&+ ]{0,9}", b["t"]) and b["t"].lower() not in
                ("subject", "session", "sesson", "date", "batch", "id", "no", "degree", "remarks")]
    session_counter: dict[str, int] = {}

    for index, ((a, b), col, median_v) in enumerate(zip(cells, readings, col_v)):
        centre = (a + b) / 2
        date = next((d for d in dates if d["x0"] - 8 <= centre <= d["x1"] + 8), None)
        merged = (b - a) > typical * 1.6
        shaded = median_v < overall_v - 18
        has_marks = any(r[0] >= RED_P_RATIO or (r[1] >= INK_TICK_RATIO and r[3] >= DOT_EXTENT) for r in col)
        if date is None or merged or shaded or not has_marks:
            continue
        d, m, y = DATE_RE.fullmatch(date["t"]).groups()
        year = int(y) + 2000 if len(y) == 2 else int(y)
        iso = f"{year:04d}-{int(m):02d}-{int(d):02d}"
        session_counter[iso] = session_counter.get(iso, 0) + 1
        subject = next((sb for sb in subjects if date["x0"] - 8 <= _cx(sb) <= date["x1"] + 8), None)
        code = re.sub(r"\s+", "", subject["t"]).upper() if subject else f"COL{index + 1}"
        columns.append(ExtractedColumn(subject_code=code, subject_name=_legend_name(legend, code),
                                       date=iso, session=session_counter[iso]))
        kept.append(index)

    students = []
    for number, row in enumerate(rows):
        marks = []
        for index in kept:
            red_ratio, ink_ratio, _, extent = readings[index][number]
            if red_ratio >= RED_P_RATIO:
                marks.append("P")
            elif extent < DOT_EXTENT:
                marks.append("")  # a dot or speck is not a tick
            elif ink_ratio >= INK_TICK_RATIO:
                marks.append("✓")
            elif ink_ratio >= INK_UNSURE_RATIO:
                marks.append("?")
            else:
                marks.append("")
        students.append(ExtractedStudent(row_number=number + 1, student_id=row["id"], full_name_khmer=khmer[number],
                                         full_name_latin=row["name"] or row["id"], gender=row["gender"],
                                         marks=marks))

    header = _header(boxes)
    logger.info("Offline scan: %d students, %d columns kept of %d cells", len(students), len(columns), len(cells))
    return ExtractedSheet(**header, columns=columns, students=students, notes=None)
