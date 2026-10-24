"""Photo scan -> database. The Claude call is replaced by a fake reader."""

import base64
import io

import pytest
from PIL import Image

from app.core.errors import AppError
from app.main import app
from app.services.sheet_reader import (
    ExtractedColumn,
    ExtractedSheet,
    ExtractedStudent,
    get_sheet_reader,
    prepare_image,
)


def fake_sheet(**overrides) -> ExtractedSheet:
    data = dict(
        faculty="Information Technology and Sciences",
        program="NP",
        major="Software Engineering",
        academic_year=4,
        semester=2,
        week=11,
        room="404",
        columns=[
            ExtractedColumn(subject_code="APP II", subject_name="Advanced Python Programming II",
                            date="2026-10-19", session=1),
            ExtractedColumn(subject_code="APP II", subject_name="Advanced Python Programming II",
                            date="2026-10-19", session=2),
            ExtractedColumn(subject_code="MIS", subject_name="Management Information System",
                            date="2026-10-20", session=1),
        ],
        students=[
            ExtractedStudent(row_number=1, student_id="00058285", full_name_khmer="ជា សិរីបុត្រ",
                             full_name_latin="CHEA SEREYBOTH", gender="M", marks=["✓", "✓", "✓"]),
            ExtractedStudent(row_number=2, student_id="00056929", full_name_khmer=None,
                             full_name_latin="CHHIN KIMLENG", gender="F", marks=["P", "P", "✓"]),
            ExtractedStudent(row_number=3, student_id="00057768", full_name_khmer=None,
                             full_name_latin="MOTH RITHYSAK", gender="M", marks=["✓", "?", "P"]),
        ],
        notes=None,
    )
    data.update(overrides)
    return ExtractedSheet(**data)


@pytest.fixture
def use_reader():
    def _install(result):
        def reader(_data: bytes):
            if isinstance(result, Exception):
                raise result
            return result
        app.dependency_overrides[get_sheet_reader] = lambda: reader
    yield _install
    app.dependency_overrides.pop(get_sheet_reader, None)


def png_bytes(size=(40, 30)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, format="PNG")
    return buffer.getvalue()


def upload(client, content=None, content_type="image/jpeg"):
    return client.post(
        "/api/attendance/scan",
        files={"file": ("sheet.jpg", content or png_bytes(), content_type)},
    )


def test_scan_saves_students_and_marks(client, make_student, use_reader):
    make_student(student_id="00058285", full_name_latin="Chea Sereyboth", gender="Male", major="Keep Me")
    use_reader(fake_sheet())

    response = upload(client)

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["students_on_sheet"] == 3
    assert result["students_registered"] == ["00056929", "00057768"]  # existing one not re-created
    assert result["attendance"]["present"] == 5
    assert result["attendance"]["not_present"] == 3
    assert result["attendance"]["blank"] == 1  # the '?' cell
    assert any("unreadable" in w and "00057768" in w for w in result["warnings"])
    assert {(a["student_id"], a["subject_code"], a["session"]) for a in result["absences"]} == {
        ("00056929", "APP II", 1), ("00056929", "APP II", 2), ("00057768", "MIS", 1),
    }

    # New students were registered from the sheet header; existing data left untouched.
    new = client.get("/api/students", params={"search": "00056929"}).json()["items"][0]
    assert (new["full_name_latin"], new["gender"], new["major"], new["academic_year"], new["semester"]) == (
        "CHHIN KIMLENG", "Female", "Software Engineering", 4, 2,
    )
    kept = client.get("/api/students", params={"search": "00058285"}).json()["items"][0]
    assert kept["major"] == "Keep Me"

    # Ticks stored as 1, P as 0.
    records = client.get("/api/attendance/records", params={"student_id": "00056929"}).json()
    assert [(r["subject_code"], r["session"], r["value"]) for r in records] == [
        ("APP II", 1, 0), ("APP II", 2, 0), ("MIS", 1, 1),
    ]
    assert records[0]["week"] == 11


def test_scan_shows_tick_or_cross_and_saves_unchecked_as_absent(client, use_reader):
    sheet = fake_sheet()
    sheet.students[0].marks = ["✓", "", "✓"]  # middle cell left empty on the paper
    use_reader(sheet)

    result = upload(client).json()

    assert [r["marks"] for r in result["rows"]] == [["✓", "✗", "✓"], ["✗", "✗", "✓"], ["✓", "?", "✗"]]
    assert result["attendance"]["present"] == 4
    assert result["attendance"]["not_present"] == 4
    records = client.get("/api/attendance/records", params={"student_id": "00058285"}).json()
    assert [r["value"] for r in records] == [1, 0, 1]


def test_scan_fixes_missing_spaces_and_fills_khmer_name(client, make_student, use_reader):
    make_student(student_id="00056929", full_name_latin="Chhinkimleng", gender="Female", full_name_khmer=None)
    make_student(student_id="00057768", full_name_latin="Moth R.", gender="Male", full_name_khmer="ម៉ូត")
    sheet = fake_sheet()
    sheet.students[1].full_name_khmer = "ជិន គឹមឡេង"
    sheet.students[2].full_name_khmer = "ម៉ូត រិទ្ធីស័ក្ក"
    use_reader(sheet)

    result = upload(client).json()

    assert "1 name(s) corrected" in result["message"]
    rows = {r["student_id"]: r for r in result["rows"]}
    assert (rows["00056929"]["full_name_latin"], rows["00056929"]["full_name_khmer"]) == ("CHHIN KIMLENG", "ជិន គឹមឡេង")
    assert rows["00058285"]["full_name_khmer"] == "ជា សិរីបុត្រ"
    # A real (different) name and an existing Khmer name are never overwritten.
    assert (rows["00057768"]["full_name_latin"], rows["00057768"]["full_name_khmer"]) == ("Moth R.", "ម៉ូត")
    saved = client.get("/api/students", params={"search": "00056929"}).json()["items"][0]
    assert (saved["full_name_latin"], saved["full_name_khmer"]) == ("CHHIN KIMLENG", "ជិន គឹមឡេង")


def test_scanning_same_sheet_twice_updates_marks(client, use_reader):
    use_reader(fake_sheet())
    upload(client)
    second = upload(client).json()

    assert second["students_registered"] == []
    assert second["attendance"]["records_created"] == 0
    assert second["attendance"]["records_updated"] == 8
    assert len(client.get("/api/attendance/records").json()) == 8


def test_invalid_student_row_is_skipped_with_warning(client, use_reader):
    sheet = fake_sheet()
    sheet.students.append(
        ExtractedStudent(row_number=4, student_id="", full_name_khmer=None,
                         full_name_latin="NO ID", gender="X", marks=["✓", "✓", "✓"])
    )
    use_reader(sheet)

    result = upload(client).json()

    assert result["students_on_sheet"] == 4
    assert len(result["rows"]) == 3
    assert any(w.startswith("Row 4") and "skipped" in w for w in result["warnings"])


def test_bad_column_date_saves_nothing(client, use_reader):
    sheet = fake_sheet()
    sheet.columns[0].date = "19/10/26"
    use_reader(sheet)

    response = upload(client)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "scan_invalid_column"
    assert client.get("/api/students").json()["total"] == 0
    assert client.get("/api/attendance/records").json() == []


def test_reader_errors_are_reported(client, use_reader):
    use_reader(AppError("Sheet scanning is not configured.", code="scan_not_configured"))
    response = upload(client)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "scan_not_configured"


def test_scan_rejects_non_images_and_requires_key(client, anon_client, use_reader):
    use_reader(fake_sheet())
    assert upload(client, b"a,b,c", content_type="text/csv").status_code == 400
    assert upload(anon_client).status_code == 401


def test_prepare_image_downscales_and_rejects_garbage():
    media_type, data = prepare_image(png_bytes(size=(5000, 1000)))
    assert media_type == "image/jpeg"
    image = Image.open(io.BytesIO(base64.b64decode(data)))
    assert max(image.size) <= 2400

    with pytest.raises(AppError):
        prepare_image(b"not an image")
