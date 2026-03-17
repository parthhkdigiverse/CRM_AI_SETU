# backend/app/modules/reports/router.py
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Optional
import io
from app.core.database import get_db
from app.modules.users.models import User, UserRole
from app.core.dependencies import RoleChecker
from app.modules.reports.schemas import DashboardStats, EmployeePerformance, BusinessSummary, ProjectPortfolio, EmployeeActivity
from app.modules.reports.service import ReportService

router = APIRouter()

# Allow admins, PMs and Sales staff to view dashboard/reports
dashboard_viewer = RoleChecker([
    UserRole.ADMIN,
    UserRole.SALES,
    UserRole.PROJECT_MANAGER,
    UserRole.PROJECT_MANAGER_AND_SALES,
    UserRole.SALES,
    UserRole.TELESALES
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
        requesting_user=current_user,
        area_id=area_id, 
        user_id=user_id, 
        start_date=start_date, 
        end_date=end_date
    )
    return stats

@router.get("/employees", response_model=List[EmployeePerformance])
def get_employee_performance(
    month: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(dashboard_viewer)
):
    return ReportService.get_employee_performance(
        db, 
        requesting_user=current_user,
        month=month, 
        start_date=start_date, 
        end_date=end_date, 
        user_id=user_id
    )

@router.get("/final", response_model=BusinessSummary)
def get_business_summary(
    month: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(dashboard_viewer)
):
    return ReportService.get_business_summary(db, month)

@router.get("/projects", response_model=List[ProjectPortfolio])
def get_project_portfolio(
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    duration: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(dashboard_viewer)
):
    return ReportService.get_project_portfolio(
        db, 
        requesting_user=current_user,
        client_id=client_id, 
        status=status, 
        duration=duration
    )

@router.get("/employees/{user_id}/activities", response_model=List[EmployeeActivity])
def get_employee_activities(
    user_id: int,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(dashboard_viewer)
):
    # RBAC: Non-admins can only see their own activities
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not authorized to view activities for other users")

    return ReportService.get_employee_activities(
        db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/export")
def export_report(
    type: str = Query(..., pattern="^(employees|final|projects)$"),
    month: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    duration: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(dashboard_viewer)
):
    if type == "employees":
        results = ReportService.get_employee_performance(
            db, requesting_user=current_user, month=month, start_date=start_date, end_date=end_date, user_id=user_id
        )
        data = []
        for r in results:
            if hasattr(r, 'model_dump'):
                data.append(r.model_dump())
            elif hasattr(r, 'dict'):
                data.append(r.dict())
            else:
                data.append(r)
        filename = f"employee_report_{datetime.now().strftime('%Y%m%d')}.csv"
    elif type == "projects":
        data = ReportService.get_project_portfolio(
            db, requesting_user=current_user, client_id=client_id, status=status, duration=duration
        )
        filename = f"client_portfolio_{datetime.now().strftime('%Y%m%d')}.csv"
    else:
        results = ReportService.get_business_summary(db, month)
        data = []
        if hasattr(results, 'model_dump'):
            data.append(results.model_dump())
        elif hasattr(results, 'dict'):
            data.append(results.dict())
        else:
            data.append(results)
        filename = f"business_summary_{datetime.now().strftime('%Y%m%d')}.csv"
        
    csv_content = ReportService.generate_csv_response(data)
    
    # Add BOM for Excel
    bom = "\uFEFF"
    full_content = bom + csv_content
    
    return Response(
        content=full_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(full_content.encode('utf-8'))),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
    )
