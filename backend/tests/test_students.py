from datetime import datetime

import pytest

from tests.conftest import student_payload


# --------------------------------------------------------------------------- create


def test_create_student_success(client):
    response = client.post("/api/students", json=student_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["student_id"] == "0012345"  # leading zeros preserved
    assert body["full_name_khmer"] == "សុខ សុភា"
    assert body["status"] == "Active"
    assert body["created_at"] and body["updated_at"]


def test_create_normalizes_input(client):
    response = client.post(
        "/api/students",
        json=student_payload(
            student_id="  e2024001 ",
            full_name_latin="  Chan   Dara  ",
            gender="male",
            semester="Semester 2",
            program="",
            status=None,
        ),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["student_id"] == "E2024001"
    assert body["full_name_latin"] == "Chan Dara"
    assert body["gender"] == "Male"
    assert body["semester"] == 2
    assert body["program"] is None
    assert body["status"] == "Active"


def test_create_rejects_duplicate_student_id(client, make_student):
    make_student(student_id="0012345")

    response = client.post("/api/students", json=student_payload(student_id="0012345"))

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "duplicate_student_id"
    assert "0012345" in error["message"]


def test_duplicate_check_is_case_insensitive(client, make_student):
    make_student(student_id="E001")
    response = client.post("/api/students", json=student_payload(student_id="e001"))
    assert response.status_code == 409


@pytest.mark.parametrize(
    "field,value",
    [
        ("gender", "Unknown"),
        ("gender", None),
        ("semester", 3),
        ("semester", 0),
        ("semester", "Semester 5"),
        ("academic_year", 0),
        ("academic_year", -1),
        ("status", "Deleted"),
        ("full_name_latin", "   "),
        ("student_id", ""),
        ("student_id", "X" * 21),
        ("student_id", "bad id!"),
    ],
)
def test_create_rejects_invalid_values(client, field, value):
    response = client.post("/api/students", json=student_payload(**{field: value}))

    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert any(d["field"] == field for d in error["details"])


def test_create_rejects_unknown_fields(client):
    response = client.post("/api/students", json=student_payload(is_admin=True))
    assert response.status_code == 422


# --------------------------------------------------------------------------- read


def test_get_student_and_not_found(client, make_student):
    created = make_student()

    response = client.get(f"/api/students/{created['id']}")
    assert response.status_code == 200
    assert response.json()["student_id"] == created["student_id"]

    missing = client.get("/api/students/999999")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "student_not_found"


def test_list_students(client, make_student):
    make_student(student_id="A001", full_name_latin="Alpha")
    make_student(student_id="A002", full_name_latin="Bravo")

    response = client.get("/api/students")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["pages"] == 1
    assert [s["student_id"] for s in body["items"]] == ["A001", "A002"]


def test_list_empty(client):
    body = client.get("/api/students").json()
    assert body == {"items": [], "total": 0, "page": 1, "page_size": 20, "pages": 0}


def test_search_by_student_id_and_names(client, make_student):
    make_student(student_id="E2024001", full_name_latin="Sok Dara", full_name_khmer="សុខ តារា")
    make_student(student_id="E2024002", full_name_latin="Chan Vibol", full_name_khmer="ចាន់ វិបុល")
    make_student(student_id="F1000", full_name_latin="Keo Dara", full_name_khmer=None)

    def ids(search):
        response = client.get("/api/students", params={"search": search})
        assert response.status_code == 200
        return sorted(s["student_id"] for s in response.json()["items"])

    assert ids("e2024") == ["E2024001", "E2024002"]
    assert ids("dara") == ["E2024001", "F1000"]
    assert ids("វិបុល") == ["E2024002"]
    assert ids("%") == []  # LIKE wildcards are escaped
    assert ids("   ") == ["E2024001", "E2024002", "F1000"]


def test_filters(client, make_student):
    make_student(student_id="S1", gender="Male", major="IT", academic_year=1, semester=1)
    make_student(student_id="S2", gender="Female", major="IT", academic_year=2, semester=2)
    make_student(student_id="S3", gender="Female", major="Math", academic_year=2, semester=1,
                 status="Inactive")

    def ids(**params):
        response = client.get("/api/students", params=params)
        assert response.status_code == 200, response.text
        return sorted(s["student_id"] for s in response.json()["items"])

    assert ids(gender="Female") == ["S2", "S3"]
    assert ids(major="IT") == ["S1", "S2"]
    assert ids(academic_year=2) == ["S2", "S3"]
    assert ids(semester=1) == ["S1", "S3"]
    assert ids(status="Inactive") == ["S3"]
    assert ids(gender="Female", major="IT") == ["S2"]


def test_invalid_filter_value_rejected(client):
    assert client.get("/api/students", params={"gender": "Robot"}).status_code == 422
    assert client.get("/api/students", params={"sort_by": "password"}).status_code == 422
    assert client.get("/api/students", params={"page_size": 1000}).status_code == 422


def test_pagination(client, make_student):
    for i in range(1, 26):
        make_student(student_id=f"P{i:03d}")

    page1 = client.get("/api/students", params={"page": 1, "page_size": 10}).json()
    page3 = client.get("/api/students", params={"page": 3, "page_size": 10}).json()

    assert page1["total"] == 25
    assert page1["pages"] == 3
    assert [s["student_id"] for s in page1["items"]][:2] == ["P001", "P002"]
    assert len(page3["items"]) == 5
    assert page3["items"][-1]["student_id"] == "P025"


def test_sorting(client, make_student):
    make_student(student_id="B", full_name_latin="Zed", academic_year=1)
    make_student(student_id="A", full_name_latin="Amy", academic_year=None)
    make_student(student_id="C", full_name_latin="Mia", academic_year=3)

    def order(**params):
        return [s["student_id"] for s in client.get("/api/students", params=params).json()["items"]]

    assert order() == ["A", "C", "B"]  # default: A-Z by Latin name, like the paper sheet
    assert order(sort_by="full_name_latin") == ["A", "C", "B"]
    assert order(sort_by="full_name_latin", sort_order="desc") == ["B", "C", "A"]
    assert order(sort_by="academic_year") == ["B", "C", "A"]  # nulls last
    assert order(sort_by="academic_year", sort_order="desc") == ["C", "B", "A"]


def test_filter_options(client, make_student):
    make_student(student_id="S1", major="IT", program="Bachelor", academic_year=1)
    make_student(student_id="S2", major="Math", program=None, academic_year=3)

    body = client.get("/api/students/filters").json()
    assert body == {"majors": ["IT", "Math"], "programs": ["Bachelor"], "academic_years": [1, 3]}


# --------------------------------------------------------------------------- update


def test_update_student(client, make_student):
    created = make_student()

    response = client.put(
        f"/api/students/{created['id']}",
        json=student_payload(full_name_latin="Sok Sophea Updated", semester=2,
                             expected_updated_at=created["updated_at"]),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["full_name_latin"] == "Sok Sophea Updated"
    assert body["semester"] == 2
    assert body["created_at"] == created["created_at"]
    assert datetime.fromisoformat(body["updated_at"]) >= datetime.fromisoformat(created["updated_at"])


def test_update_rejects_stale_version(client, make_student):
    created = make_student()
    first = client.put(
        f"/api/students/{created['id']}",
        json=student_payload(major="Physics", expected_updated_at=created["updated_at"]),
    )
    assert first.status_code == 200

    # A second editor still holds the original timestamp.
    stale = client.put(
        f"/api/students/{created['id']}",
        json=student_payload(major="Chemistry", expected_updated_at="2000-01-01T00:00:00+00:00"),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "stale_update"
    assert client.get(f"/api/students/{created['id']}").json()["major"] == "Physics"


def test_update_rejects_duplicate_student_id(client, make_student):
    make_student(student_id="A1")
    second = make_student(student_id="A2")

    response = client.put(f"/api/students/{second['id']}", json=student_payload(student_id="A1"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_student_id"


def test_update_not_found(client):
    response = client.put("/api/students/424242", json=student_payload())
    assert response.status_code == 404


def test_update_validation(client, make_student):
    created = make_student()
    response = client.put(f"/api/students/{created['id']}", json=student_payload(semester=9))
    assert response.status_code == 422


# --------------------------------------------------------------------------- deactivate


def test_deactivate_student(client, make_student):
    created = make_student()

    response = client.delete(f"/api/students/{created['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "Inactive"
    # The record still exists (soft delete).
    fetched = client.get(f"/api/students/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "Inactive"
    # Idempotent.
    assert client.delete(f"/api/students/{created['id']}").status_code == 200


def test_deactivate_not_found(client):
    assert client.delete("/api/students/987654").status_code == 404


def test_reactivate_with_put(client, make_student):
    created = make_student()
    client.delete(f"/api/students/{created['id']}")
    response = client.put(f"/api/students/{created['id']}", json=student_payload(status="Active"))
    assert response.json()["status"] == "Active"


# --------------------------------------------------------------------------- authorization


def test_write_endpoints_require_api_key(anon_client):
    assert anon_client.get("/api/students").status_code == 200

    response = anon_client.post("/api/students", json=student_payload())
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"

    assert anon_client.put("/api/students/1", json=student_payload()).status_code == 401
    assert anon_client.delete("/api/students/1").status_code == 401
    assert anon_client.get("/api/students/export").status_code == 401

    wrong = anon_client.post(
        "/api/students", json=student_payload(), headers={"X-API-Key": "wrong"}
    )
    assert wrong.status_code == 401
