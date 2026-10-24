"""Test fixtures.

Tests run against a separate PostgreSQL database (TEST_DATABASE_URL), never the real
one. The schema is built with the real Alembic migrations, and the table is truncated
after every test.
"""

import os

import pytest
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_files = {
    **dotenv_values(os.path.join(BACKEND_DIR, "..", ".env")),
    **dotenv_values(os.path.join(BACKEND_DIR, ".env")),
}

TEST_DATABASE_URL = (
    os.environ.get("TEST_DATABASE_URL")
    or _env_files.get("TEST_DATABASE_URL")
    or "postgresql+psycopg2://postgres:postgres@localhost:5432/attendance_test_db"
)
TEST_API_KEY = "test-admin-key"

if "test" not in (make_url(TEST_DATABASE_URL).database or ""):
    raise RuntimeError(
        "Refusing to run tests: TEST_DATABASE_URL must point to a database whose name "
        "contains 'test' so real student data is never touched."
    )

# Configure the application BEFORE it is imported.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ADMIN_API_KEY"] = TEST_API_KEY
os.environ["ENVIRONMENT"] = "test"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    cfg.attributes["database_url"] = TEST_DATABASE_URL
    cfg.attributes["configure_logger"] = False
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_students():
    yield
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE attendance_records, class_sessions, subjects, students "
                "RESTART IDENTITY CASCADE"
            )
        )
    engine.dispose()


@pytest.fixture
def client():
    with TestClient(app, headers={"X-API-Key": TEST_API_KEY}) as c:
        yield c


@pytest.fixture
def anon_client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def student_payload(**overrides) -> dict:
    payload = {
        "student_id": "0012345",
        "full_name_khmer": "សុខ សុភា",
        "full_name_latin": "Sok Sophea",
        "gender": "Female",
        "program": "Bachelor",
        "major": "Computer Science",
        "academic_year": 2,
        "semester": 1,
        "status": "Active",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def make_student(client):
    def _make(**overrides) -> dict:
        response = client.post("/api/students", json=student_payload(**overrides))
        assert response.status_code == 201, response.text
        return response.json()

    return _make
