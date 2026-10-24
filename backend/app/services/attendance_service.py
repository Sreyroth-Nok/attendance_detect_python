"""Business logic for saving attendance sheets and reading attendance records."""

from sqlalchemy import func, literal_column, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

import datetime as dt

from pydantic import ValidationError

from app.core.errors import AppError
from app.models.attendance import AttendanceRecord, ClassSession, Subject
from app.models.student import Student
from app.schemas.attendance import (
    AttendanceRecordRead,
    AttendanceSheetIn,
    AttendanceSheetResult,
    ScanAbsence,
    ScanResult,
    SheetColumn,
    SheetRow,
)
from app.schemas.student import StudentCreate
from app.services.sheet_reader import ExtractedSheet

PRESENT_MARKS = {"✓", "✔", "√", "V", "/", "1", "TRUE", "PRESENT"}
NOT_PRESENT_MARKS = {"P", "X", "✗", "✘", "0", "FALSE"}


def parse_mark(mark: str | None) -> bool | None:
    """Tick -> True (1), 'P' or a cross -> False (0), empty -> None (not stored)."""
    if mark is None:
        return None
    normalized = mark.strip().upper()
    if not normalized:
        return None
    if normalized in PRESENT_MARKS:
        return True
    if normalized in NOT_PRESENT_MARKS:
        return False
    raise ValueError(mark)


def _get_or_create_subject(db: Session, code: str, name: str | None) -> Subject:
    subject = db.scalar(select(Subject).where(Subject.code == code))
    if subject is None:
        # "APPII" (OCR) and "APP II" are the same subject.
        compact = code.replace(" ", "")
        subject = db.scalar(select(Subject).where(func.replace(Subject.code, " ", "") == compact))
    if subject is None:
        subject = Subject(code=code, name=name or code)
        db.add(subject)
        db.flush()
    elif name and subject.name == subject.code:
        subject.name = name  # replace a placeholder name, never a real one
    return subject


def _get_or_create_session(db: Session, subject: Subject, column, week, room) -> ClassSession:
    session = db.scalar(
        select(ClassSession).where(
            ClassSession.subject_id == subject.id,
            ClassSession.session_date == column.date,
            ClassSession.session_number == column.session,
        )
    )
    if session is None:
        session = ClassSession(
            subject_id=subject.id,
            session_date=column.date,
            session_number=column.session,
            week=week,
            room=room,
        )
        db.add(session)
        db.flush()
    else:
        session.week = week if week is not None else session.week
        session.room = room or session.room
    return session


def save_sheet(db: Session, sheet: AttendanceSheetIn, *, commit: bool = True) -> AttendanceSheetResult:
    """Validate the whole sheet first, then save everything in one transaction.

    Saving the same sheet again updates the existing marks instead of duplicating them.
    """
    ids = [row.student_id for row in sheet.rows]
    students = dict(db.execute(select(Student.student_id, Student.id).where(Student.student_id.in_(ids))).all())
    unknown = [sid for sid in ids if sid not in students]

    bad_marks = []
    parsed: list[list[bool | None]] = []
    for row in sheet.rows:
        values = []
        for column, mark in zip(sheet.columns, row.marks):
            try:
                values.append(parse_mark(mark))
            except ValueError:
                bad_marks.append(
                    f"{row.student_id} / {column.subject_code} {column.date} S{column.session}: '{mark}'"
                )
                values.append(None)
        parsed.append(values)

    if unknown or bad_marks:
        details = {}
        if unknown:
            details["unknown_students"] = unknown
        if bad_marks:
            details["invalid_marks"] = bad_marks
        raise AppError(
            "Nothing was saved. Register the unknown students first and use only a tick or 'P' "
            "as marks.",
            code="invalid_sheet",
            details=details,
        )

    sessions = [
        _get_or_create_session(
            db, _get_or_create_subject(db, c.subject_code, c.subject_name), c, sheet.week, sheet.room
        )
        for c in sheet.columns
    ]

    values, raw_marks = [], []
    blank = 0
    for row, row_values in zip(sheet.rows, parsed):
        for session, mark, value in zip(sessions, row.marks, row_values):
            if value is None:
                blank += 1
                continue
            values.append(
                {
                    "class_session_id": session.id,
                    "student_id": students[row.student_id],
                    "is_present": value,
                    "raw_mark": mark.strip()[:10],
                }
            )
            raw_marks.append(value)

    created = updated = 0
    if values:
        stmt = insert(AttendanceRecord).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_attendance_records_session_student",
            set_={
                "is_present": stmt.excluded.is_present,
                "raw_mark": stmt.excluded.raw_mark,
                "updated_at": literal_column("now()"),
            },
        ).returning(literal_column("(xmax = 0)"))
        inserted_flags = db.scalars(stmt).all()
        created = sum(1 for flag in inserted_flags if flag)
        updated = len(inserted_flags) - created

    if commit:
        db.commit()

    present = sum(1 for v in raw_marks if v)
    return AttendanceSheetResult(
        message=f"Saved {len(values)} attendance mark(s) for {len(sheet.rows)} student(s) "
        f"across {len(sessions)} session(s).",
        sessions=len(sessions),
        records_created=created,
        records_updated=updated,
        present=present,
        not_present=len(raw_marks) - present,
        blank=blank,
    )


def list_records(
    db: Session,
    *,
    student_id: str | None = None,
    subject_code: str | None = None,
    is_present: bool | None = None,
    limit: int = 1000,
) -> list[AttendanceRecordRead]:
    stmt = (
        select(AttendanceRecord, Student, ClassSession, Subject)
        .join(Student, AttendanceRecord.student_id == Student.id)
        .join(ClassSession, AttendanceRecord.class_session_id == ClassSession.id)
        .join(Subject, ClassSession.subject_id == Subject.id)
    )
    if student_id:
        stmt = stmt.where(Student.student_id == student_id.strip().upper())
    if subject_code:
        stmt = stmt.where(Subject.code == subject_code.strip().upper())
    if is_present is not None:
        stmt = stmt.where(AttendanceRecord.is_present == is_present)
    stmt = stmt.order_by(
        ClassSession.session_date, Subject.code, ClassSession.session_number, Student.student_id
    ).limit(limit)

    return [
        AttendanceRecordRead(
            student_id=student.student_id,
            full_name_khmer=student.full_name_khmer,
            full_name_latin=student.full_name_latin,
            gender=student.gender,
            major=student.major,
            academic_year=student.academic_year,
            program=student.program,
            subject_code=subject.code,
            subject_name=subject.name,
            date=session.session_date,
            session=session.session_number,
            week=session.week,
            is_present=record.is_present,
            value=int(record.is_present),
            raw_mark=record.raw_mark,
        )
        for record, student, session, subject in db.execute(stmt).all()
    ]


# --------------------------------------------------------------------------- photo scan

GENDER_CODES = {"M": "Male", "F": "Female", "MALE": "Male", "FEMALE": "Female"}


def _sheet_columns(extracted: ExtractedSheet) -> list[SheetColumn]:
    columns = []
    for index, col in enumerate(extracted.columns, start=1):
        try:
            columns.append(SheetColumn(subject_code=col.subject_code, subject_name=col.subject_name,
                                       date=dt.date.fromisoformat(col.date), session=col.session))
        except (ValueError, ValidationError) as exc:
            raise AppError(
                f"Column {index} ({col.subject_code} {col.date} S{col.session}) could not be read. "
                "Nothing was saved; try a clearer photo.",
                code="scan_invalid_column",
            ) from exc
    return columns


def _sheet_value(value: int | None, low: int, high: int) -> int | None:
    return value if value is not None and low <= value <= high else None


def scan_sheet(db: Session, extracted: ExtractedSheet) -> ScanResult:
    """Save everything read from a sheet photo in one transaction.

    New students are registered from the sheet header (program, major, year, semester);
    existing students are left unchanged, except that a missing Khmer name is filled in and a
    Latin name that differs only in spaces or capitals ("Cheasereyboth") is set as on the sheet. A tick is present (✓);
    a P or an empty cell is not present (✗). Unreadable cells ('?') are skipped and reported.
    """
    columns = _sheet_columns(extracted)
    if not columns:
        raise AppError("No attendance columns with marks were found on the sheet.", code="scan_no_columns")
    if not extracted.students:
        raise AppError("No students were found on the sheet.", code="scan_no_students")

    warnings: list[str] = []
    if extracted.notes:
        warnings.append(f"Reader note: {extracted.notes}")

    existing = {s.student_id: s for s in db.scalars(select(Student))}
    corrected: list[str] = []
    registered: list[str] = []
    sheet_rows: list[SheetRow] = []
    saved_rows: list[dict] = []
    names: dict[str, str] = {}

    for st in extracted.students:
        label = f"Row {st.row_number}"
        latin = st.full_name_latin  # kept exactly as printed on the sheet (e.g. "CHEA SEREYBOTH")
        try:
            student = StudentCreate(
                student_id=st.student_id,
                full_name_khmer=st.full_name_khmer,
                full_name_latin=latin,
                gender=GENDER_CODES.get((st.gender or "").strip().upper(), st.gender),
                program=extracted.program,
                major=extracted.major,
                academic_year=_sheet_value(extracted.academic_year, 1, 10),
                semester=_sheet_value(extracted.semester, 1, 2),
            )
        except ValidationError as exc:
            problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
            warnings.append(f"{label} ({st.student_id} {st.full_name_latin}) skipped: {problems}")
            continue

        if student.student_id in names:
            warnings.append(f"{label}: student {student.student_id} appears twice; second row skipped.")
            continue

        known = existing.get(student.student_id)
        if known is not None:
            changed = False
            if not known.full_name_khmer and student.full_name_khmer:
                known.full_name_khmer, changed = student.full_name_khmer, True
            # Same letters, only spacing or capitals differ -> use the sheet's version.
            same_letters = (known.full_name_latin.replace(" ", "").lower()
                            == student.full_name_latin.replace(" ", "").lower())
            if (same_letters and known.full_name_latin != student.full_name_latin
                    and " " in student.full_name_latin.strip()):
                known.full_name_latin, changed = student.full_name_latin, True
            if changed:
                corrected.append(student.student_id)
        else:
            db.add(Student(**student.model_dump(mode="json")))
            registered.append(student.student_id)
            if " " not in student.full_name_latin.strip():
                warnings.append(f"{label}: new student {student.student_id} registered as "
                                f"'{student.full_name_latin}'. Check the spelling and spaces on the Students page.")

        marks = list(st.marks[: len(columns)])
        if len(st.marks) != len(columns):
            warnings.append(f"{label} ({student.student_id}): {len(st.marks)} marks read for "
                            f"{len(columns)} columns; missing cells left blank.")
            marks += [""] * (len(columns) - len(marks))

        clean, shown = [], []
        for col, mark in zip(columns, marks):
            try:
                # Columns only exist when some student has a mark, so an empty cell is "not checked".
                present = parse_mark(mark) is True
                clean.append(mark if mark.strip() else "✗")
                shown.append("✓" if present else "✗")
            except ValueError:
                warnings.append(f"{label} ({student.student_id}) {col.subject_code} {col.date:%d/%m} "
                                f"S{col.session}: mark '{mark}' unreadable, not saved - check the paper.")
                clean.append("")
                shown.append("?")

        names[student.student_id] = known.full_name_latin if known else student.full_name_latin
        sheet_rows.append(SheetRow(student_id=student.student_id, marks=clean))
        saved_rows.append({"row": st.row_number, "student_id": student.student_id,
                           "full_name_khmer": known.full_name_khmer if known else student.full_name_khmer,
                           "full_name_latin": known.full_name_latin if known else student.full_name_latin,
                           "marks": shown})

    if not sheet_rows:
        raise AppError("None of the student rows could be read. Nothing was saved.", code="scan_no_students")

    try:
        db.flush()  # make newly registered students visible to save_sheet
        attendance = save_sheet(
            db,
            AttendanceSheetIn(week=_sheet_value(extracted.week, 1, 60), room=extracted.room,
                              columns=columns, rows=sheet_rows),
            commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    absences = [
        ScanAbsence(student_id=row.student_id, full_name_latin=names[row.student_id],
                    subject_code=col.subject_code, date=col.date, session=col.session)
        for row in sheet_rows
        for col, mark in zip(columns, row.marks)
        if parse_mark(mark) is False
    ]

    return ScanResult(
        message=f"Read {len(sheet_rows)} student(s) and saved {attendance.present + attendance.not_present} "
        f"mark(s): {attendance.present} present ✓ (1), {attendance.not_present} not present ✗ (0). "
        f"{len(registered)} new student(s) registered"
        + (f", {len(corrected)} name(s) corrected." if corrected else "."),
        sheet={"faculty": extracted.faculty, "program": extracted.program, "major": extracted.major,
               "academic_year": extracted.academic_year, "semester": extracted.semester,
               "week": extracted.week, "room": extracted.room},
        columns=columns,
        students_on_sheet=len(extracted.students),
        students_registered=registered,
        attendance=attendance,
        absences=absences,
        rows=saved_rows,
        warnings=warnings,
    )
