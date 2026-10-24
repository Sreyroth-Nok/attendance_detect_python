import csv
import io

HEADER = "student_id,full_name_khmer,full_name_latin,gender,program,major,academic_year,semester,status\n"


def upload(client, text: str, *, skip_invalid: bool = False, filename: str = "students.csv",
           bom: bool = False):
    data = text.encode("utf-8-sig" if bom else "utf-8")
    return client.post(
        "/api/students/import",
        params={"skip_invalid": str(skip_invalid).lower()},
        files={"file": (filename, data, "text/csv")},
    )


def all_ids(client) -> list[str]:
    items = client.get("/api/students", params={"page_size": 100, "sort_by": "student_id"}).json()["items"]
    return [s["student_id"] for s in items]


# --------------------------------------------------------------------------- import


def test_import_valid_file(client):
    text = HEADER + (
        "0001,សុខ សុភា,Sok Sophea,Female,Bachelor,Computer Science,1,Semester 1,Active\n"
        "0002,,Chan Dara,male,Bachelor,Computer Science,2,2,\n"
    )

    response = upload(client, text, bom=True)

    assert response.status_code == 200, response.text
    report = response.json()
    assert report["status"] == "completed"
    assert report["imported"] == 2
    assert report["failed"] == 0
    assert [r["student_id"] for r in report["saved"]] == ["0001", "0002"]
    assert all_ids(client) == ["0001", "0002"]


def test_import_rejects_whole_file_when_any_row_invalid(client):
    text = HEADER + (
        "0001,,Valid Student,Female,,,1,1,Active\n"
        "0002,,Bad Gender,Robot,,,1,1,Active\n"
        "0003,,Bad Semester,Male,,,1,3,Active\n"
        ",,Missing Id,Male,,,1,1,Active\n"
    )

    report = upload(client, text).json()

    assert report["status"] == "rejected"
    assert report["imported"] == 0
    assert report["failed"] == 3
    assert report["total_rows"] == 4
    rows = {e["row"]: e for e in report["errors"]}
    assert set(rows) == {3, 4, 5}
    assert any("gender" in msg for msg in rows[3]["errors"])
    assert any("semester" in msg for msg in rows[4]["errors"])
    assert any("student_id" in msg for msg in rows[5]["errors"])
    assert all_ids(client) == []  # nothing saved


def test_import_skip_invalid_saves_only_valid_rows(client):
    text = HEADER + (
        "0001,,Valid One,Female,,,1,1,Active\n"
        "0002,,Bad Gender,Robot,,,1,1,Active\n"
        "0003,,Valid Two,Male,,,,,\n"
    )

    report = upload(client, text, skip_invalid=True).json()

    assert report["status"] == "partial"
    assert report["imported"] == 2
    assert report["failed"] == 1
    assert [r["student_id"] for r in report["saved"]] == ["0001", "0003"]
    assert report["errors"][0]["row"] == 3
    assert "NOT saved" in report["message"]
    assert all_ids(client) == ["0001", "0003"]


def test_import_detects_duplicates_in_file_and_database(client, make_student):
    make_student(student_id="0001")
    text = HEADER + (
        "0001,,Already Exists,Female,,,1,1,Active\n"
        "0002,,First,Male,,,1,1,Active\n"
        "0002,,Repeated,Male,,,1,1,Active\n"
    )

    report = upload(client, text).json()

    assert report["status"] == "rejected"
    messages = {e["row"]: " ".join(e["errors"]) for e in report["errors"]}
    assert "already registered" in messages[2]
    assert "duplicated in this file" in messages[4] and "line 3" in messages[4]
    assert all_ids(client) == ["0001"]


def test_import_missing_required_columns(client):
    response = upload(client, "student_id,gender\n001,Male\n")
    assert response.status_code == 400
    assert "full_name_latin" in response.json()["error"]["message"]


def test_import_rejects_non_csv_and_bad_encoding(client):
    assert upload(client, HEADER, filename="students.xlsx").status_code == 400
    bad = client.post(
        "/api/students/import",
        files={"file": ("s.csv", HEADER.encode() + "0001,,Caf\xe9,Male".encode("latin-1"), "text/csv")},
    )
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "invalid_encoding"


def test_import_empty_file(client):
    assert upload(client, "").status_code == 400
    report = upload(client, HEADER + "\n\n").json()
    assert report["status"] == "rejected"
    assert report["total_rows"] == 0


def test_import_requires_api_key(anon_client):
    response = anon_client.post(
        "/api/students/import", files={"file": ("s.csv", HEADER.encode(), "text/csv")}
    )
    assert response.status_code == 401


# --------------------------------------------------------------------------- export


def test_export_csv(client, make_student):
    make_student(student_id="0002", full_name_latin="Second", major="IT")
    make_student(student_id="0001", full_name_latin="First", full_name_khmer="ទីមួយ", major="Math")

    response = client.get("/api/students/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    text = response.content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert [r["student_id"] for r in rows] == ["0001", "0002"]  # leading zeros kept
    assert rows[0]["full_name_khmer"] == "ទីមួយ"
    assert "created_at" in rows[0]


def test_export_respects_filters(client, make_student):
    make_student(student_id="0001", major="IT")
    make_student(student_id="0002", major="Math")

    text = client.get("/api/students/export", params={"major": "Math"}).content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert [r["student_id"] for r in rows] == ["0002"]


def test_export_neutralizes_formula_injection(client, make_student):
    make_student(student_id="0001", full_name_latin="=HYPERLINK(\"x\")")
    text = client.get("/api/students/export").content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows[0]["full_name_latin"].startswith("'=")


def test_export_then_import_roundtrip(client, make_student):
    make_student(student_id="0001", full_name_khmer="សុខ")
    exported = client.get("/api/students/export").content.decode("utf-8-sig")
    client.delete("/api/students/1")

    # Re-importing the same IDs must be reported as duplicates, not silently merged.
    report = upload(client, exported).json()
    assert report["status"] == "rejected"
    assert "already registered" in report["errors"][0]["errors"][0]
