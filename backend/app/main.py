"""FastAPI application entry point.

Run locally (from the backend folder):  uvicorn app.main:app --reload
Swagger UI: http://localhost:8000/docs   ReDoc: http://localhost:8000/redoc
"""

import logging
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.db.session import get_db
from app.routers import attendance, dashboard, students

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")


def create_app() -> FastAPI:
    settings = get_settings()

    if settings.is_production and not settings.admin_api_key:
        raise RuntimeError("ADMIN_API_KEY must be set when ENVIRONMENT=production.")
    if not settings.admin_api_key:
        logger.warning("ADMIN_API_KEY is empty: write endpoints are unprotected (development only).")

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Student Management module of the Attendance Detection System.\n\n"
            "Write operations and CSV export require the `X-API-Key` header when the server "
            "has `ADMIN_API_KEY` configured. In Swagger UI click **Authorize** and enter the key."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-API-Key"],
        expose_headers=["Content-Disposition"],
    )

    register_exception_handlers(app)
    app.include_router(students.router)
    app.include_router(dashboard.router)
    app.include_router(attendance.router)

    @app.get("/api/health", tags=["System"], summary="API and database health check")
    def health(db: Annotated[Session, Depends(get_db)]):
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
            "write_protection": bool(settings.admin_api_key),
        }

    return app


app = create_app()
