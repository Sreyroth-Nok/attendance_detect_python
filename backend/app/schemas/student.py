"""Pydantic schemas: request validation, input normalization and response shapes.

The same `StudentCreate` schema validates JSON requests and CSV import rows, so the
rules are defined exactly once.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

STUDENT_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_\-/.]{0,19}$")
_WHITESPACE = re.compile(r"\s+")


class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class StudentStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"


def _clean_text(value: Any) -> Any:
    """Trim and collapse internal whitespace; turn blank strings into None."""
    if isinstance(value, str):
        value = _WHITESPACE.sub(" ", value).strip()
        return value or None
    return value


def _match_choice(value: Any, enum_cls: type[Enum]) -> Any:
    """Accept enum values case-insensitively (e.g. 'male', ' FEMALE ')."""
    if isinstance(value, str):
        lowered = value.strip().lower()
        for member in enum_cls:
            if member.value.lower() == lowered:
                return member
    return value


def _parse_semester(value: Any) -> Any:
    """Accept 1, '1', 'Semester 1', 'S1'."""
    if isinstance(value, str):
        match = re.fullmatch(r"(?:semester|sem|s)?\s*([0-9]+)", value.strip(), flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return value


class StudentFields(BaseModel):
    """Fields shared by create and update requests."""

    student_id: str = Field(
        max_length=20,
        description="University student ID. Stored as text so leading zeros are preserved. "
        "Normalized to upper case.",
        examples=["e20230001"],
    )
    full_name_khmer: str | None = Field(default=None, max_length=150, examples=["សុខ សុភា"])
    full_name_latin: str = Field(max_length=150, examples=["Sok Sophea"])
    gender: Gender
    program: str | None = Field(default=None, max_length=100, examples=["Bachelor"])
    major: str | None = Field(default=None, max_length=150, examples=["Computer Science"])
    academic_year: int | None = Field(default=None, ge=1, le=10, description="Year of study, 1-10")
    semester: int | None = Field(default=None, ge=1, le=2, description="1 or 2")
    status: StudentStatus = StudentStatus.ACTIVE

    @field_validator("full_name_khmer", "program", "major", "academic_year", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> Any:
        return _clean_text(value)

    @field_validator("student_id", mode="before")
    @classmethod
    def _normalize_student_id(cls, value: Any) -> Any:
        value = _clean_text(value)
        if value is None:
            raise ValueError("Student ID is required")
        if isinstance(value, int):
            value = str(value)
        if isinstance(value, str):
            value = value.upper()
            if not STUDENT_ID_PATTERN.fullmatch(value):
                raise ValueError(
                    "Student ID must be 1-20 characters: letters, digits, '-', '_', '/' or '.'"
                )
        return value

    @field_validator("full_name_latin", mode="before")
    @classmethod
    def _require_latin_name(cls, value: Any) -> Any:
        value = _clean_text(value)
        if value is None:
            raise ValueError("Full name (Latin) is required")
        return value

    @field_validator("gender", mode="before")
    @classmethod
    def _normalize_gender(cls, value: Any) -> Any:
        value = _clean_text(value)
        if value is None:
            raise ValueError("Gender is required")
        return _match_choice(value, Gender)

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, value: Any) -> Any:
        value = _clean_text(value)
        if value is None:
            return StudentStatus.ACTIVE
        return _match_choice(value, StudentStatus)

    @field_validator("semester", mode="before")
    @classmethod
    def _normalize_semester(cls, value: Any) -> Any:
        return _parse_semester(_clean_text(value))


class StudentCreate(StudentFields):
    model_config = ConfigDict(extra="forbid")


class StudentUpdate(StudentFields):
    model_config = ConfigDict(extra="forbid")

    expected_updated_at: datetime | None = Field(
        default=None,
        description="The `updated_at` value the client last saw. If the record changed since "
        "then, the update is rejected with 409 to prevent overwriting someone else's edit.",
    )


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: str
    full_name_khmer: str | None
    full_name_latin: str
    gender: Gender
    program: str | None
    major: str | None
    academic_year: int | None
    semester: int | None
    status: StudentStatus
    created_at: datetime
    updated_at: datetime


SortField = Literal[
    "student_id",
    "full_name_khmer",
    "full_name_latin",
    "gender",
    "program",
    "major",
    "academic_year",
    "semester",
    "status",
    "created_at",
    "updated_at",
]


class StudentFilterParams(BaseModel):
    """Filters shared by the list and export endpoints."""

    search: str | None = Field(default=None, max_length=100, description="Student ID or name")
    gender: Gender | None = None
    major: str | None = Field(default=None, max_length=150)
    academic_year: int | None = Field(default=None, ge=1, le=10)
    semester: int | None = Field(default=None, ge=1, le=2)
    status: StudentStatus | None = None

    @field_validator("search", "major", mode="before")
    @classmethod
    def _blank_to_none(cls, value: Any) -> Any:
        return _clean_text(value)


class StudentListParams(StudentFilterParams):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: SortField = "full_name_latin"  # A-Z by Latin name, like the paper attendance sheet
    sort_order: Literal["asc", "desc"] = "asc"


class StudentListResponse(BaseModel):
    items: list[StudentRead]
    total: int
    page: int
    page_size: int
    pages: int


class FilterOptions(BaseModel):
    majors: list[str]
    programs: list[str]
    academic_years: list[int]


class ImportRowError(BaseModel):
    row: int = Field(description="Line number in the CSV file (the header is line 1)")
    student_id: str | None
    errors: list[str]


class ImportSavedRow(BaseModel):
    row: int
    student_id: str


class ImportReport(BaseModel):
    status: Literal["completed", "partial", "rejected"] = Field(
        description="completed: every row saved; partial: valid rows saved and invalid rows "
        "skipped; rejected: nothing saved because at least one row was invalid"
    )
    message: str
    total_rows: int
    imported: int
    failed: int
    saved: list[ImportSavedRow]
    errors: list[ImportRowError]
