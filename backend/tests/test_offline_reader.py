"""Offline reader on a synthetic sheet: printed text + blue ticks + red P + dots + a shaded column."""

import cv2
import numpy as np
import pytest

from app.services.offline_reader import _split_points, read_sheet_offline
from tests.test_attendance import COLUMNS, sheet

BLUE = (170, 60, 20)   # BGR
RED = (40, 30, 200)
FONT = cv2.FONT_HERSHEY_SIMPLEX

STUDENTS = [("00058285", "CHEA SEREYBOTH", "M"), ("00056929", "CHHIN KIMLENG", "F"),
            ("00057768", "MOTH RITHYSAK", "M"), ("056612", "VUTH KUNTHY", "F")]  # some sheets print 6-digit IDs
# Columns: APP II s1, s2 | MIS s1, s2 | BT (shaded, no class)
MARKS = [["✓", "✓", "✓", "✓"], ["P", "P", "✓", "✓"], ["✓", "✓", "P", "P"], ["✓", "✓", "✓", ""]]
DOTS = {(3, 3)}  # (row, column) cells with a small pen dot: not a tick, read as empty


def draw_sheet() -> bytes:
    w, h = 1300, 520
    img = np.full((h, w, 3), (215, 230, 215), np.uint8)  # light green paper
    text = lambda s, x, y, scale=0.6: cv2.putText(img, s, (x, y), FONT, scale, (30, 30, 30), 1, cv2.LINE_AA)
    text("Major: Software Engineering", 760, 40)
    text("Program: NP", 40, 40)
    text("Year: 4, Semester: II", 40, 70)
    text("Week 11", 1150, 40)
    text("Room: 404", 760, 70)

    x_gender, x_marks, cell, x_batch = 520, 560, 60, 900
    top, row_h = 190, 50
    for i, (label, sub) in enumerate([("19/10/26", "APP II"), ("20/10/26", "MIS"), ("21/10/26", "BT")]):
        x = x_marks + i * 2 * cell
        text(label, x + 15, 120, 0.55)
        text(sub, x + 30, 150, 0.6)
    text("Batch", x_batch + 10, 150)

    bottom = top + row_h * len(STUDENTS)
    cv2.rectangle(img, (x_marks + 4 * cell, top), (x_marks + 6 * cell, bottom), (150, 165, 150), -1)  # BT shaded
    for r in range(len(STUDENTS) + 1):
        cv2.line(img, (30, top + r * row_h), (x_batch + 150, top + r * row_h), (20, 20, 20), 2)
    for x in [30, 200, 480, x_gender + 30] + [x_marks + c * cell for c in range(7) if c != 5] + [x_batch + 150]:
        cv2.line(img, (x, top), (x, bottom), (20, 20, 20), 2)

    for r, ((sid, name, gender), marks) in enumerate(zip(STUDENTS, MARKS)):
        y = top + r * row_h + 33
        text(sid, 50, y)
        text(name, 220, y)
        text(gender, x_gender, y)
        text("6 (1st)", x_batch + 20, y)
        for c, mark in enumerate(marks):
            x0 = x_marks + c * cell
            if mark == "✓":
                cv2.line(img, (x0 + 18, y - 14), (x0 + 27, y - 2), BLUE, 3)
                cv2.line(img, (x0 + 27, y - 2), (x0 + 45, y - 30), BLUE, 3)
            elif mark == "P":
                cv2.putText(img, "P", (x0 + 20, y), FONT, 0.9, RED, 3, cv2.LINE_AA)
            if (r, c) in DOTS:
                cv2.circle(img, (x0 + 30, y - 6), 2, BLUE, -1)
    ok, png = cv2.imencode(".png", img)
    return png.tobytes()


@pytest.fixture(scope="module")
def result():
    return read_sheet_offline(draw_sheet())


def test_reads_header(result):
    assert (result.major, result.program, result.academic_year, result.semester, result.week, result.room) == (
        "Software Engineering", "NP", 4, 2, 11, "404")


def test_reads_columns_and_skips_shaded(result):
    assert [(c.subject_code, c.date, c.session) for c in result.columns] == [
        ("APPII", "2026-10-19", 1), ("APPII", "2026-10-19", 2),
        ("MIS", "2026-10-20", 1), ("MIS", "2026-10-20", 2),
    ]


def test_reads_students_and_marks(result):
    assert [(s.student_id, s.gender) for s in result.students] == [(i, g) for i, _, g in STUDENTS]
    assert [s.marks for s in result.students] == MARKS


def test_reads_latin_names_with_spaces(result):
    assert [s.full_name_latin for s in result.students] == [n for _, n, _ in STUDENTS]


def test_space_from_reread_is_mapped_onto_original_letters():
    assert _split_points("CHHINKIMLENG", "CHIN KIMLENG") == {5}  # re-read dropped an H
    assert _split_points("KEOPHOL", "KEO PHOL") == {3}
    assert _split_points("CHEASEREYBOTH", "SOMETHING ELSE") == set()  # unrelated re-read ignored


def test_rejects_non_image():
    from app.core.errors import AppError

    with pytest.raises(AppError):
        read_sheet_offline(b"not an image")


def test_ocr_code_without_spaces_maps_to_existing_subject(client, make_student):
    make_student(student_id="00056929", full_name_latin="Chhin Kimleng", gender="Female")
    client.post("/api/attendance/sheets", json=sheet([{"student_id": "00056929", "marks": ["P", "P", "✓"]}]))
    ocr_columns = [{"subject_code": "APPII", "subject_name": "Advanced Python Programming Il",
                    "date": "2026-10-19", "session": 1}]

    result = client.post("/api/attendance/sheets",
                         json=sheet([{"student_id": "00056929", "marks": ["✓"]}], columns=ocr_columns)).json()

    assert result["records_updated"] == 1 and result["records_created"] == 0
    codes = {r["subject_code"] for r in client.get("/api/attendance/records").json()}
    assert codes == {"APP II", "MIS"}


assert COLUMNS  # shared fixture data imported from test_attendance
