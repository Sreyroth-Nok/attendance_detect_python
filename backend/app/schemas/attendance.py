"""Schemas for saving a paper attendance sheet and reading attendance records."""

import re
import datetime as dt
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_WHITESPACE = re.compile(r"\s+")


class SheetColumn(BaseModel):
    """One mark column on the sheet: a subject on a date, session 1 or 2."""

    subject_code: str = Field(min_length=1, max_length=20, examples=["APP II"])
    subject_name: str | None = Field(default=None, max_length=150,
                                     examples=["Advanced Python Programming II"])
    date: dt.date
    session: int = Field(ge=1, le=4)

    @field_validator("subject_code", "subject_name", mode="before")
    @classmethod
    def _clean(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = _WHITESPACE.sub(" ", value).strip()
            return value or None
        return value

    @field_validator("subject_code")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()


class SheetRow(BaseModel):
    student_id: str = Field(min_length=1, max_length=20, description="University student ID")
    marks: list[str | None] = Field(
        description="One mark per column: a tick (✓ ✔ √ V 1) = present, P (or 0) = not "
        "present, empty/null = no class or not recorded."
    )

    @field_validator("student_id", mode="before")
    @classmethod
    def _normalize_id(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value


class AttendanceSheetIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    week: int | None = Field(default=None, ge=1, le=60)
    room: str | None = Field(default=None, max_length=50)
    columns: list[SheetColumn] = Field(min_length=1, max_length=40)
    rows: list[SheetRow] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _check_shape(self) -> "AttendanceSheetIn":
        keys = [(c.subject_code, c.date, c.session) for c in self.columns]
        if len(set(keys)) != len(keys):
            raise ValueError("The same subject/date/session column appears more than once.")
        seen: set[str] = set()
        for row in self.rows:
            if len(row.marks) != len(self.columns):
                raise ValueError(
                    f"Student {row.student_id} has {len(row.marks)} marks but the sheet has "
                    f"{len(self.columns)} columns."
                )
            if row.student_id in seen:
                raise ValueError(f"Student {row.student_id} appears more than once.")
            seen.add(row.student_id)
        return self


class AttendanceSheetResult(BaseModel):
    message: str
    sessions: int
    records_created: int
    records_updated: int
    present: int = Field(description="Marks saved as 1 / true")
    not_present: int = Field(description="Marks saved as 0 / false (P or cross)")
    blank: int = Field(description="Empty cells, not stored")


class ScanAbsence(BaseModel):
    student_id: str
    full_name_latin: str
    subject_code: str
    date: dt.date
    session: int


class ScanResult(BaseModel):
    message: str
    sheet: dict = Field(description="Header details read from the sheet")
    columns: list[SheetColumn]
    students_on_sheet: int
    students_registered: list[str] = Field(description="IDs of students added because they were new")
    attendance: AttendanceSheetResult
    absences: list[ScanAbsence] = Field(description="Every mark saved as 0 (P or not checked)")
    rows: list[dict] = Field(description="Per student: id, Khmer and Latin name, marks ('✓' present, '✗' not, '?' unreadable)")
    warnings: list[str]


class AttendanceRecordRead(BaseModel):
    student_id: str
    full_name_khmer: str | None
    full_name_latin: str
    gender: str
    major: str | None
    academic_year: int | None
    program: str | None
    subject_code: str
    subject_name: str
    date: dt.date
    session: int
    week: int | None
    is_present: bool
    value: int = Field(description="1 = present, 0 = P")
    raw_mark: str
