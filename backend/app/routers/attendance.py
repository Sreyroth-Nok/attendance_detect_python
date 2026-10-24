"""Attendance endpoints under /api/attendance."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import AdminRequired
from app.db.session import get_db
from app.schemas.attendance import (
    AttendanceRecordRead,
    AttendanceSheetIn,
    AttendanceSheetResult,
    ScanResult,
)
from app.services import attendance_service
from app.services.sheet_reader import SheetReader, get_sheet_reader

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/sheets",
    response_model=AttendanceSheetResult,
    summary="Save a paper attendance sheet",
    dependencies=[AdminRequired],
)
def save_sheet(db: DbSession, sheet: AttendanceSheetIn):
    """Stores every mark: tick = present (true / 1), `P` = not present (false / 0), and blank
    cells are skipped. All-or-nothing: unknown students or invalid marks save nothing.
    Re-sending the same sheet updates marks instead of duplicating them."""
    return attendance_service.save_sheet(db, sheet)


@router.post(
    "/scan",
    response_model=ScanResult,
    summary="Upload a photo of an attendance sheet and save it",
    dependencies=[AdminRequired],
)
async def scan_sheet(
    db: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    reader: Annotated[SheetReader, Depends(get_sheet_reader)],
    file: Annotated[UploadFile, File(description="Photo of the sheet (JPG, PNG or WebP)")],
):
    """Reads the sheet with Claude vision and saves it immediately: new students are
    registered, ticks are stored as 1 (✓) and P or an unchecked cell as 0 (✗). Unreadable
    cells are skipped and listed in `warnings`."""
    if file.content_type not in IMAGE_TYPES:
        raise AppError("Please upload a photo (JPG, PNG or WebP).", code="invalid_file_type")
    data = await file.read(settings.max_scan_bytes + 1)
    if len(data) > settings.max_scan_bytes:
        raise AppError(f"The photo is larger than {settings.max_scan_bytes // (1024 * 1024)} MB.",
                       code="file_too_large")

    # The Claude call is blocking and can take a minute; keep it off the event loop.
    extracted = await run_in_threadpool(reader, data)
    return attendance_service.scan_sheet(db, extracted)


@router.get("/records", response_model=list[AttendanceRecordRead], summary="List attendance marks")
def list_records(
    db: DbSession,
    student_id: Annotated[str | None, Query(max_length=20)] = None,
    subject_code: Annotated[str | None, Query(max_length=20)] = None,
    is_present: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
):
    return attendance_service.list_records(
        db, student_id=student_id, subject_code=subject_code, is_present=is_present, limit=limit
    )
