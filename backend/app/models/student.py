"""Student ORM model.

`id` is the surrogate key that future tables (attendance records, enrollments,
face-recognition profiles) should reference with foreign keys. `student_id` is the
university-issued business identifier and is stored as text to keep leading zeros.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Identity,
    Index,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

GENDERS = ("Male", "Female", "Other")
STATUSES = ("Active", "Inactive")
SEMESTERS = (1, 2)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    student_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    full_name_khmer: Mapped[str | None] = mapped_column(String(150))
    full_name_latin: Mapped[str] = mapped_column(String(150), nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    program: Mapped[str | None] = mapped_column(String(100))
    major: Mapped[str | None] = mapped_column(String(150))
    academic_year: Mapped[int | None] = mapped_column(SmallInteger)
    semester: Mapped[int | None] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="Active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("gender IN ('Male', 'Female', 'Other')", name="gender_valid"),
        CheckConstraint("semester IS NULL OR semester IN (1, 2)", name="semester_valid"),
        CheckConstraint("status IN ('Active', 'Inactive')", name="status_valid"),
        CheckConstraint("academic_year IS NULL OR academic_year > 0", name="academic_year_positive"),
        CheckConstraint("char_length(btrim(student_id)) > 0", name="student_id_not_blank"),
        CheckConstraint("char_length(btrim(full_name_latin)) > 0", name="full_name_latin_not_blank"),
        Index("ix_students_status", "status"),
        Index("ix_students_major", "major"),
        Index("ix_students_full_name_latin", "full_name_latin"),
    )

    def __repr__(self) -> str:
        return f"<Student id={self.id} student_id={self.student_id!r}>"
