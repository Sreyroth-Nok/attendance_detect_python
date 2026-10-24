def test_dashboard_stats_empty(client):
    body = client.get("/api/dashboard/stats").json()
    assert body == {
        "total_students": 0,
        "active_students": 0,
        "inactive_students": 0,
        "by_major": [],
        "by_gender": [],
    }


def test_dashboard_stats(client, make_student):
    make_student(student_id="S1", major="IT", gender="Male")
    make_student(student_id="S2", major="IT", gender="Female")
    make_student(student_id="S3", major="IT", gender="Female", status="Inactive")
    make_student(student_id="S4", major="Math", gender="Other")
    make_student(student_id="S5", major=None, gender="Male")

    response = client.get("/api/dashboard/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["total_students"] == 5
    assert body["active_students"] == 4
    assert body["inactive_students"] == 1
    assert body["by_major"] == [
        {"major": "IT", "total": 3, "active": 2},
        {"major": "Math", "total": 1, "active": 1},
        {"major": "Unassigned", "total": 1, "active": 1},
    ]
    assert body["by_gender"] == [
        {"gender": "Female", "total": 2},
        {"gender": "Male", "total": 2},
        {"gender": "Other", "total": 1},
    ]
