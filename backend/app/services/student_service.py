"""Business logic for student management.

Routers stay thin: they parse HTTP input and delegate here. All database access goes
through SQLAlchemy expressions, so every value is sent as a bound parameter.
"""

import csv
import io
import math
from collections.abc import Sequence

from pydantic import ValidationError
from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.models.student import Student
from app.schemas.dashboard import DashboardStats, GenderCount, MajorCount
from app.schemas.student import (
    FilterOptions,
    ImportReport,
    ImportRowError,
    ImportSavedRow,
    StudentCreate,
    StudentFilterParams,
    StudentListParams,
    StudentStatus,
    StudentUpdate,
)

CSV_COLUMNS = [
    "student_id",
    "full_name_khmer",
    "full_name_latin",
    "gender",
    "program",
    "major",
    "academic_year",
    "semester",
    "status",
]
EXPORT_COLUMNS = CSV_COLUMNS + ["created_at", "updated_at"]
REQUIRED_CSV_COLUMNS = {"student_id", "full_name_latin", "gender"}

STUDENT_ID_CONSTRAINT = "uq_students_student_id"


# --------------------------------------------------------------------------- queries


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _apply_filters(stmt: Select, filters: StudentFilterParams) -> Select:
    if filters.search:
        pattern = f"%{_escape_like(filters.search)}%"
        stmt = stmt.where(
            or_(
                Student.student_id.ilike(pattern, escape="\\"),
                Student.full_name_latin.ilike(pattern, escape="\\"),
                Student.full_name_khmer.ilike(pattern, escape="\\"),
            )
        )
    if filters.gender:
        stmt = stmt.where(Student.gender == filters.gender.value)
    if filters.major:
        stmt = stmt.where(Student.major == filters.major)
    if filters.academic_year is not None:
        stmt = stmt.where(Student.academic_year == filters.academic_year)
    if filters.semester is not None:
        stmt = stmt.where(Student.semester == filters.semester)
    if filters.status:
        stmt = stmt.where(Student.status == filters.status.value)
    return stmt


def list_students(db: Session, params: StudentListParams) -> dict:
    base = _apply_filters(select(Student), params)

    total = db.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0

    sort_column = getattr(Student, params.sort_by)
    order = sort_column.asc() if params.sort_order == "asc" else sort_column.desc()
    # Stable ordering across pages: nulls last, then the primary key as a tie-breaker.
    stmt = (
        base.order_by(order.nulls_last(), Student.id.asc())
        .offset((params.page - 1) * params.page_size)
        .limit(params.page_size)
    )
    items = db.scalars(stmt).all()

    return {
        "items": items,
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "pages": math.ceil(total / params.page_size) if total else 0,
    }


def get_student(db: Session, pk: int) -> Student:
    student = db.get(Student, pk)
    if student is None:
        raise NotFoundError(f"Student with id {pk} was not found.", code="student_not_found")
    return student


def _student_id_taken(db: Session, student_id: str, exclude_pk: int | None = None) -> bool:
    stmt = select(Student.id).where(Student.student_id == student_id)
    if exclude_pk is not None:
        stmt = stmt.where(Student.id != exclude_pk)
    return db.scalar(stmt) is not None


def _duplicate_error(student_id: str) -> ConflictError:
    return ConflictError(
        f"A student with ID '{student_id}' already exists.",
        code="duplicate_student_id",
        details=[{"field": "student_id", "message": "This student ID is already registered."}],
    )


def _is_student_id_violation(exc: IntegrityError) -> bool:
    diag = getattr(exc.orig, "diag", None)
    return getattr(diag, "constraint_name", None) == STUDENT_ID_CONSTRAINT


def _commit_or_raise(db: Session, student_id: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # A concurrent request can insert the same ID between our check and the commit;
        # the unique constraint is the final guard.
        if _is_student_id_violation(exc):
            raise _duplicate_error(student_id) from exc
        raise


# --------------------------------------------------------------------------- writes


def create_student(db: Session, data: StudentCreate) -> Student:
    if _student_id_taken(db, data.student_id):
        raise _duplicate_error(data.student_id)

    student = Student(**data.model_dump(mode="json"))
    db.add(student)
    _commit_or_raise(db, data.student_id)
    db.refresh(student)
    return student


def update_student(db: Session, pk: int, data: StudentUpdate) -> Student:
    # Lock the row so two simultaneous updates are applied one after the other.
    student = db.scalar(select(Student).where(Student.id == pk).with_for_update())
    if student is None:
        raise NotFoundError(f"Student with id {pk} was not found.", code="student_not_found")

    if data.expected_updated_at is not None and student.updated_at != data.expected_updated_at:
        db.rollback()
        raise ConflictError(
            "This student was changed by someone else after you opened it. "
            "Reload the record and apply your changes again.",
            code="stale_update",
        )

    if data.student_id != student.student_id and _student_id_taken(db, data.student_id, pk):
        db.rollback()
        raise _duplicate_error(data.student_id)

    for field, value in data.model_dump(mode="json", exclude={"expected_updated_at"}).items():
        setattr(student, field, value)

    _commit_or_raise(db, data.student_id)
    db.refresh(student)
    return student


def deactivate_student(db: Session, pk: int) -> Student:
    """Soft delete: records are never removed so future attendance history stays intact."""
    student = get_student(db, pk)
    if student.status != StudentStatus.INACTIVE.value:
        student.status = StudentStatus.INACTIVE.value
        db.commit()
        db.refresh(student)
    return student


# --------------------------------------------------------------------------- read models


def dashboard_stats(db: Session) -> DashboardStats:
    is_active = Student.status == StudentStatus.ACTIVE.value

    total, active = db.execute(
        select(func.count(Student.id), func.count(Student.id).filter(is_active))
    ).one()

    major_label = func.coalesce(Student.major, "Unassigned").label("major")
    major_rows = db.execute(
        select(major_label, func.count(Student.id), func.count(Student.id).filter(is_active))
        .group_by(major_label)
        .order_by(func.count(Student.id).desc(), major_label)
    ).all()

    gender_rows = db.execute(
        select(Student.gender, func.count(Student.id))
        .group_by(Student.gender)
        .order_by(Student.gender)
    ).all()

    return DashboardStats(
        total_students=total,
        active_students=active,
        inactive_students=total - active,
        by_major=[MajorCount(major=m, total=t, active=a) for m, t, a in major_rows],
        by_gender=[GenderCount(gender=g, total=t) for g, t in gender_rows],
    )


def filter_options(db: Session) -> FilterOptions:
    def distinct(column) -> list:
        return list(db.scalars(select(column).where(column.is_not(None)).distinct().order_by(column)))

    return FilterOptions(
        majors=distinct(Student.major),
        programs=distinct(Student.program),
        academic_years=distinct(Student.academic_year),
    )


# --------------------------------------------------------------------------- CSV


def _format_row_errors(exc: ValidationError) -> list[str]:
    messages = []
    for err in exc.errors():
        field = ".".join(str(part) for part in err["loc"]) or "row"
        message = err["msg"].removeprefix("Value error, ")
        messages.append(f"{field}: {message}")
    return messages


def _decode_csv(content: bytes) -> str:
    try:
        # utf-8-sig strips the BOM that Excel adds when saving "CSV UTF-8".
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError(
            "The file is not valid UTF-8. In Excel choose 'CSV UTF-8 (Comma delimited)'.",
            code="invalid_encoding",
        ) from exc


def import_students_csv(
    db: Session, content: bytes, *, skip_invalid: bool, max_rows: int
) -> ImportReport:
    """Validate every row, then save in a single transaction.

    skip_invalid=False (default): all-or-nothing. Any invalid row rejects the whole file.
    skip_invalid=True: valid rows are saved and invalid rows are reported as skipped.
    """
    reader = csv.DictReader(io.StringIO(_decode_csv(content)))
    if not reader.fieldnames:
        raise AppError("The CSV file is empty or has no header row.", code="invalid_csv")

    header_map = {
        name: name.strip().lower().replace(" ", "_") for name in reader.fieldnames if name
    }
    present = set(header_map.values())
    missing = REQUIRED_CSV_COLUMNS - present
    if missing:
        raise AppError(
            f"Missing required column(s): {', '.join(sorted(missing))}.",
            code="invalid_csv",
            details={"expected_columns": CSV_COLUMNS},
        )

    valid: list[tuple[int, StudentCreate]] = []
    errors: list[ImportRowError] = []
    first_seen: dict[str, int] = {}
    total_rows = 0

    for raw in reader:
        row_number = reader.line_num
        values = {
            header_map[key]: value
            for key, value in raw.items()
            if key in header_map and header_map[key] in CSV_COLUMNS
        }
        if not any((value or "").strip() for value in values.values()):
            continue  # ignore blank lines
        total_rows += 1
        if total_rows > max_rows:
            raise AppError(
                f"The file has more than {max_rows} rows. Split it into smaller files.",
                code="too_many_rows",
            )

        raw_id = (values.get("student_id") or "").strip() or None
        try:
            student = StudentCreate.model_validate(values)
        except ValidationError as exc:
            errors.append(
                ImportRowError(row=row_number, student_id=raw_id, errors=_format_row_errors(exc))
            )
            continue

        if student.student_id in first_seen:
            errors.append(
                ImportRowError(
                    row=row_number,
                    student_id=student.student_id,
                    errors=[
                        f"student_id: duplicated in this file (first seen on line "
                        f"{first_seen[student.student_id]})"
                    ],
                )
            )
            continue
        first_seen[student.student_id] = row_number
        valid.append((row_number, student))

    # One query to find IDs that already exist in the database.
    existing: set[str] = set()
    ids = [s.student_id for _, s in valid]
    for start in range(0, len(ids), 1000):
        chunk = ids[start : start + 1000]
        existing.update(db.scalars(select(Student.student_id).where(Student.student_id.in_(chunk))))

    to_save: list[tuple[int, StudentCreate]] = []
    for row_number, student in valid:
        if student.student_id in existing:
            errors.append(
                ImportRowError(
                    row=row_number,
                    student_id=student.student_id,
                    errors=["student_id: already registered in the system"],
                )
            )
        else:
            to_save.append((row_number, student))

    errors.sort(key=lambda e: e.row)

    if total_rows == 0:
        return ImportReport(
            status="rejected", message="The file contains no student rows.",
            total_rows=0, imported=0, failed=0, saved=[], errors=[],
        )

    if errors and not skip_invalid:
        return ImportReport(
            status="rejected",
            message=f"No students were imported because {len(errors)} row(s) have errors. "
            "Fix the rows listed below and upload the file again, or choose to import only "
            "the valid rows.",
            total_rows=total_rows,
            imported=0,
            failed=len(errors),
            saved=[],
            errors=errors,
        )

    if to_save:
        db.add_all(Student(**s.model_dump(mode="json")) for _, s in to_save)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ConflictError(
                "Another user registered some of these student IDs while the file was being "
                "imported. No rows were saved; please upload the file again.",
                code="import_conflict",
            ) from exc

    saved = [ImportSavedRow(row=r, student_id=s.student_id) for r, s in to_save]
    if errors:
        status, message = "partial", (
            f"Imported {len(saved)} student(s). {len(errors)} row(s) were skipped because of "
            "errors and were NOT saved."
        )
    else:
        status, message = "completed", f"Imported all {len(saved)} student(s)."

    return ImportReport(
        status=status,
        message=message,
        total_rows=total_rows,
        imported=len(saved),
        failed=len(errors),
        saved=saved,
        errors=errors,
    )


def _csv_safe(value: object) -> object:
    """Neutralize spreadsheet formula injection (cells starting with = + - @)."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def export_students_csv(db: Session, filters: StudentFilterParams) -> str:
    stmt = _apply_filters(select(Student), filters).order_by(Student.student_id)
    students: Sequence[Student] = db.scalars(stmt).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_COLUMNS)
    for s in students:
        writer.writerow(
            [_csv_safe(getattr(s, col)) for col in CSV_COLUMNS]
            + [s.created_at.isoformat(), s.updated_at.isoformat()]
        )
    return buffer.getvalue()
