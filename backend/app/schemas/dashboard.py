from pydantic import BaseModel


class MajorCount(BaseModel):
    major: str
    total: int
    active: int


class GenderCount(BaseModel):
    gender: str
    total: int


class DashboardStats(BaseModel):
    total_students: int
    active_students: int
    inactive_students: int
    by_major: list[MajorCount]
    by_gender: list[GenderCount]
