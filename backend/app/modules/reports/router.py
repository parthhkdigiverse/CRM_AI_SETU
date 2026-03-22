from fastapi import APIRouter, Depends, Query, Body, HTTPException, Response
from datetime import datetime
from typing import List, Optional, Any
from app.modules.users.models import User, UserRole
from app.core.dependencies import RoleChecker
from app.modules.reports.schemas import DashboardStats, EmployeePerformance, BusinessSummary, ProjectPortfolio, EmployeeActivity, PerformanceNoteRead
from app.modules.reports.service import ReportService

router = APIRouter()

dashboard_viewer = RoleChecker([
    UserRole.ADMIN,
    UserRole.SALES,
    UserRole.PROJECT_MANAGER,
    UserRole.PROJECT_MANAGER_AND_SALES,
    UserRole.TELESALES
])

@router.get("/employees/{user_id}/notes", response_model=List[PerformanceNoteRead])
async def get_employee_notes(user_id: str, current_user: User = Depends(dashboard_viewer)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    service = ReportService()
    return await service.get_performance_notes(user_id)

@router.post("/employees/{user_id}/notes")
async def add_employee_note(user_id: str, note: str = Body(..., embed=True), current_user: User = Depends(dashboard_viewer)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    service = ReportService()
    return await service.add_performance_note(user_id, current_user.id, note)

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(area_id: Optional[str] = Query(None), user_id: Optional[str] = Query(None), start_date: Optional[str] = Query(None), end_date: Optional[str] = Query(None), current_user: User = Depends(dashboard_viewer)):
    service = ReportService()
    return await service.get_dashboard_stats(requesting_user=current_user, area_id=area_id, user_id=user_id, start_date=start_date, end_date=end_date)

@router.get("/employees", response_model=List[EmployeePerformance])
async def get_employee_performance(month: Optional[str] = Query(None), start_date: Optional[str] = Query(None), end_date: Optional[str] = Query(None), user_id: Optional[str] = Query(None), current_user: User = Depends(dashboard_viewer)):
    service = ReportService()
    return await service.get_employee_performance(requesting_user=current_user, month=month, start_date=start_date, end_date=end_date, user_id=user_id)

@router.get("/final", response_model=BusinessSummary)
async def get_business_summary(month: Optional[str] = Query(None), current_user: User = Depends(dashboard_viewer)):
    service = ReportService()
    return await service.get_business_summary(month)

@router.get("/projects", response_model=List[ProjectPortfolio])
async def get_project_portfolio(client_id: Optional[str] = Query(None), status: Optional[str] = Query(None), duration: Optional[str] = Query(None), current_user: User = Depends(dashboard_viewer)):
    service = ReportService()
    return await service.get_project_portfolio(requesting_user=current_user, client_id=client_id, status=status, duration=duration)

@router.get("/employees/{user_id}/activities", response_model=List[EmployeeActivity])
async def get_employee_activities(user_id: str, start_date: Optional[str] = Query(None), end_date: Optional[str] = Query(None), current_user: User = Depends(dashboard_viewer)):
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view activities for other users")
    service = ReportService()
    return await service.get_employee_activities(user_id=user_id, start_date=start_date, end_date=end_date)

@router.get("/export")
async def export_report(type: str = Query(..., pattern="^(employees|final|projects)$"), month: Optional[str] = Query(None), start_date: Optional[str] = Query(None), end_date: Optional[str] = Query(None), user_id: Optional[str] = Query(None), client_id: Optional[str] = Query(None), status: Optional[str] = Query(None), duration: Optional[str] = Query(None), current_user: User = Depends(dashboard_viewer)):
    service = ReportService()
    if type == "employees":
        results = await service.get_employee_performance(requesting_user=current_user, month=month, start_date=start_date, end_date=end_date, user_id=user_id)
        filename = f"employee_report_{datetime.now().strftime('%Y%m%d')}.csv"
        data = results
    elif type == "projects":
        results = await service.get_project_portfolio(requesting_user=current_user, client_id=client_id, status=status, duration=duration)
        filename = f"client_portfolio_{datetime.now().strftime('%Y%m%d')}.csv"
        data = results
    else:
        results = await service.get_business_summary(month)
        filename = f"business_summary_{datetime.now().strftime('%Y%m%d')}.csv"
        data = [results]
        
    csv_content = service.generate_csv_response(data)
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
