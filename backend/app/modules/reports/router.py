from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.users.models import User, UserRole
from app.core.dependencies import RoleChecker
from app.modules.reports.schemas import DashboardStats
from app.modules.reports.service import ReportService

router = APIRouter()

# Allow admins and PMs to view dashboard stats
dashboard_viewer = RoleChecker([
    UserRole.ADMIN,
    UserRole.PROJECT_MANAGER,
    UserRole.PROJECT_MANAGER_AND_SALES
])

@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(dashboard_viewer)
):
    stats = ReportService.get_dashboard_stats(db)
    return stats
