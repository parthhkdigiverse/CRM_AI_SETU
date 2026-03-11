# backend/app/modules/reports/router.py
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import io
from app.core.database import get_db
from app.modules.users.models import User, UserRole
from app.core.dependencies import RoleChecker
from app.modules.reports.schemas import DashboardStats, EmployeePerformance, BusinessSummary
from app.modules.reports.service import ReportService

router = APIRouter()

# Allow admins and PMs to view dashboard stats
dashboard_viewer = RoleChecker([
    UserRole.ADMIN,
    UserRole.SALES,
    UserRole.PROJECT_MANAGER,
    UserRole.PROJECT_MANAGER_AND_SALES
])

@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    area_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(dashboard_viewer)
):
    stats = ReportService.get_dashboard_stats(
        db, 
        area_id=area_id, 
        user_id=user_id, 
        start_date=start_date, 
        end_date=end_date
    )
    return stats

@router.get("/employees", response_model=List[EmployeePerformance])
def get_employee_performance(
    month: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(dashboard_viewer)
):
    return ReportService.get_employee_performance(db, month)

@router.get("/final", response_model=BusinessSummary)
def get_business_summary(
    month: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(dashboard_viewer)
):
    return ReportService.get_business_summary(db, month)

@router.get("/export")
def export_report(
    type: str = Query(..., pattern="^(employees|final)$"),
    month: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(dashboard_viewer)
):
    if type == "employees":
        data = ReportService.get_employee_performance(db, month)
        filename = f"employee_report_{month or 'current'}.csv"
    else:
        data = [ReportService.get_business_summary(db, month)]
        filename = f"business_summary_{month or 'current'}.csv"
        
    csv_content = ReportService.generate_csv_response(data)
    
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
