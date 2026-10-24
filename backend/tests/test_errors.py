"""Database failures must return a generic JSON error without leaking internals."""

from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app


class BrokenSession:
    def _fail(self, *args, **kwargs):
        raise OperationalError(
            "SELECT * FROM students",
            {},
            Exception('password authentication failed for user "postgres" at 10.0.0.5'),
        )

    execute = scalar = scalars = get = commit = _fail

    def rollback(self):
        pass

    def close(self):
        pass


def _broken_db():
    yield BrokenSession()


def test_database_error_is_hidden(anon_client):
    app.dependency_overrides[get_db] = _broken_db
    try:
        response = anon_client.get("/api/students")
        health = anon_client.get("/api/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "database_error"
    text = response.text.lower()
    assert "password" not in text
    assert "select" not in text
    assert "postgres" not in text
    assert "traceback" not in text
    assert health.status_code == 503


def test_unknown_route_uses_error_envelope(anon_client):
    response = anon_client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"


def test_health(anon_client):
    body = anon_client.get("/api/health").json()
    assert body == {"status": "ok", "database": "connected", "write_protection": True}


def test_openapi_docs_available(anon_client):
    assert anon_client.get("/docs").status_code == 200
    schema = anon_client.get("/openapi.json").json()
    assert "/api/students" in schema["paths"]
    assert "/api/dashboard/stats" in schema["paths"]
