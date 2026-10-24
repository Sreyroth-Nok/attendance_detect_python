"""Dashboard endpoints under /api/dashboard."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import DashboardStats
from app.services import student_service

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats, summary="Student statistics")
def get_stats(db: Annotated[Session, Depends(get_db)]):
    return student_service.dashboard_stats(db)
