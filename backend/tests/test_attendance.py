import pytest

from app.services.attendance_service import parse_mark

COLUMNS = [
    {"subject_code": "APP II", "subject_name": "Advanced Python Programming II", "date": "2026-10-19", "session": 1},
    {"subject_code": "APP II", "date": "2026-10-19", "session": 2},
    {"subject_code": "MIS", "subject_name": "Management Information System", "date": "2026-10-20", "session": 1},
]


def sheet(rows, columns=COLUMNS, **extra):
    return {"week": 11, "room": "404", "columns": columns, "rows": rows, **extra}


@pytest.fixture
def two_students(make_student):
    make_student(student_id="00056929", full_name_latin="Chhin Kimleng", gender="Female")
    make_student(student_id="00058285", full_name_latin="Chea Sereyboth", gender="Male")


@pytest.mark.parametrize(
    "mark,expected",
    [("✓", True), ("✔", True), ("√", True), ("v", True), ("1", True),
     ("P", False), (" p ", False), ("0", False), ("", None), (None, None)],
)
def test_parse_mark(mark, expected):
    assert parse_mark(mark) is expected


def test_parse_mark_rejects_unknown():
    with pytest.raises(ValueError):
        parse_mark("A")


def test_save_sheet_tick_is_1_and_p_is_0(client, two_students):
    response = client.post(
        "/api/attendance/sheets",
        json=sheet([
            {"student_id": "00056929", "marks": ["P", "P", "✓"]},
            {"student_id": "00058285", "marks": ["✓", "✓", None]},
        ]),
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["sessions"] == 3
    assert result["records_created"] == 5
    assert result["present"] == 3
    assert result["not_present"] == 2
    assert result["blank"] == 1

    records = client.get("/api/attendance/records", params={"student_id": "00056929"}).json()
    assert [(r["subject_code"], r["session"], r["value"], r["is_present"]) for r in records] == [
        ("APP II", 1, 0, False),
        ("APP II", 2, 0, False),
        ("MIS", 1, 1, True),
    ]
    assert records[0]["week"] == 11
    absent = client.get("/api/attendance/records", params={"is_present": "false"}).json()
    assert len(absent) == 2


def test_resaving_sheet_updates_instead_of_duplicating(client, two_students):
    rows = [{"student_id": "00056929", "marks": ["P", "P", "✓"]}]
    client.post("/api/attendance/sheets", json=sheet(rows))

    corrected = [{"student_id": "00056929", "marks": ["✓", "P", "✓"]}]
    result = client.post("/api/attendance/sheets", json=sheet(corrected)).json()

    assert result["records_created"] == 0
    assert result["records_updated"] == 3
    records = client.get("/api/attendance/records").json()
    assert len(records) == 3
    assert records[0]["value"] == 1


def test_unknown_student_or_bad_mark_saves_nothing(client, two_students):
    response = client.post(
        "/api/attendance/sheets",
        json=sheet([
            {"student_id": "00056929", "marks": ["✓", "A", "✓"]},
            {"student_id": "99999999", "marks": ["✓", "✓", "✓"]},
        ]),
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "invalid_sheet"
    assert error["details"]["unknown_students"] == ["99999999"]
    assert "'A'" in error["details"]["invalid_marks"][0]
    assert client.get("/api/attendance/records").json() == []


def test_sheet_shape_validation(client, two_students):
    wrong_count = sheet([{"student_id": "00056929", "marks": ["✓"]}])
    assert client.post("/api/attendance/sheets", json=wrong_count).status_code == 422

    duplicate_column = sheet([{"student_id": "00056929", "marks": ["✓", "✓"]}], columns=COLUMNS[:1] * 2)
    assert client.post("/api/attendance/sheets", json=duplicate_column).status_code == 422


def test_save_sheet_requires_api_key(anon_client):
    response = anon_client.post(
        "/api/attendance/sheets", json=sheet([{"student_id": "X", "marks": ["✓", "✓", "✓"]}])
    )
    assert response.status_code == 401
