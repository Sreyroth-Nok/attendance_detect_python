"""Student REST endpoints under /api/students."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Path, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import AdminRequired
from app.db.session import get_db
from app.schemas.student import (
    FilterOptions,
    ImportReport,
    StudentCreate,
    StudentFilterParams,
    StudentListParams,
    StudentListResponse,
    StudentRead,
    StudentUpdate,
)
from app.services import student_service

router = APIRouter(prefix="/api/students", tags=["Students"])

DbSession = Annotated[Session, Depends(get_db)]
StudentPk = Annotated[int, Path(ge=1, description="Internal numeric id of the student record")]


@router.get("", response_model=StudentListResponse, summary="List students")
def list_students(db: DbSession, params: Annotated[StudentListParams, Query()]):
    """Paginated list with search (student ID or Khmer/Latin name), filters and sorting."""
    return student_service.list_students(db, params)


@router.get(
    "/export",
    summary="Export students to CSV",
    dependencies=[AdminRequired],
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}, "description": "UTF-8 CSV file"}},
)
def export_students(db: DbSession, filters: Annotated[StudentFilterParams, Query()]):
    """Exports the students matching the same filters as the list endpoint."""
    csv_text = student_service.export_students_csv(db, filters)
    filename = f"students_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.csv"
    # The BOM lets Excel detect UTF-8 so Khmer names display correctly.
    return Response(
        content="﻿" + csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/import",
    response_model=ImportReport,
    summary="Import students from CSV",
    dependencies=[AdminRequired],
)
async def import_students(
    db: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File(description="UTF-8 CSV using the template columns")],
    skip_invalid: Annotated[
        bool,
        Query(description="false: reject the whole file if any row is invalid. "
              "true: save valid rows and report the skipped ones."),
    ] = False,
):
    if file.filename and not file.filename.lower().endswith(".csv"):
        raise AppError("Please upload a .csv file.", code="invalid_file_type")

    content = await file.read(settings.max_import_bytes + 1)
    if len(content) > settings.max_import_bytes:
        raise AppError(
            f"The file is larger than {settings.max_import_bytes // (1024 * 1024)} MB.",
            code="file_too_large",
        )
    return student_service.import_students_csv(
        db, content, skip_invalid=skip_invalid, max_rows=settings.max_import_rows
    )


@router.get("/filters", response_model=FilterOptions, summary="Values for filter dropdowns")
def get_filter_options(db: DbSession):
    return student_service.filter_options(db)


@router.get("/{id}", response_model=StudentRead, summary="Get one student")
def get_student(db: DbSession, id: StudentPk):
    return student_service.get_student(db, id)


@router.post(
    "",
    response_model=StudentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a student",
    dependencies=[AdminRequired],
    responses={409: {"description": "Student ID already exists"}},
)
def create_student(db: DbSession, payload: StudentCreate):
    return student_service.create_student(db, payload)


@router.put(
    "/{id}",
    response_model=StudentRead,
    summary="Update a student",
    dependencies=[AdminRequired],
    responses={409: {"description": "Duplicate student ID or stale update"}},
)
def update_student(db: DbSession, id: StudentPk, payload: StudentUpdate):
    return student_service.update_student(db, id, payload)


@router.delete(
    "/{id}",
    response_model=StudentRead,
    summary="Deactivate a student (soft delete)",
    dependencies=[AdminRequired],
)
def deactivate_student(db: DbSession, id: StudentPk):
    """Sets the status to Inactive. Records are never physically deleted, so the
    student's future attendance history remains valid. Reactivate with PUT."""
    return student_service.deactivate_student(db, id)
