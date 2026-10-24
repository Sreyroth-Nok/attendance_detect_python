"""Attendance ORM models: subjects, class sessions and per-student attendance marks.

One paper attendance sheet maps to several class sessions (one per subject/date/session
column), and each tick or "P" on the sheet becomes one AttendanceRecord.
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (CheckConstraint("char_length(btrim(code)) > 0", name="code_not_blank"),)


class ClassSession(Base):
    __tablename__ = "class_sessions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    session_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    week: Mapped[int | None] = mapped_column(SmallInteger)
    room: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    subject: Mapped[Subject] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "subject_id", "session_date", "session_number", name="uq_class_sessions_subject_date_number"
        ),
        CheckConstraint("session_number BETWEEN 1 AND 4", name="session_number_valid"),
        CheckConstraint("week IS NULL OR week > 0", name="week_positive"),
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    class_session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False
    )
    # References students.id (internal key), not the university student number.
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    # True (1) = present (tick on the sheet), False (0) = "P" on the sheet.
    is_present: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # The mark exactly as written on the sheet, kept for auditing.
    raw_mark: Mapped[str] = mapped_column(String(10), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("class_session_id", "student_id", name="uq_attendance_records_session_student"),
        Index("ix_attendance_records_student_id", "student_id"),
    )
