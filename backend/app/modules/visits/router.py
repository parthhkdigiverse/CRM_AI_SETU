from datetime import datetime, timezone
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, status as http_status, Request, UploadFile, File, Form, HTTPException
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.visits.schemas import VisitCreate, VisitRead, VisitUpdate, VisitStatus
from app.modules.visits.service import VisitService

router = APIRouter()

create_access = RoleChecker([UserRole.SALES, UserRole.TELESALES, UserRole.ADMIN])
read_access = RoleChecker([UserRole.SALES, UserRole.TELESALES, UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])

@router.post("/", response_model=VisitRead, status_code=http_status.HTTP_201_CREATED)
async def create_visit(
    request: Request,
    shop_id: str = Form(...),
    remarks: str = Form(...),
    status: str = Form(...),
    visit_date: Optional[str] = Form(None),
    decline_remarks: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    current_user: User = Depends(create_access)
) -> Any:
    if current_user.role in [UserRole.SALES, UserRole.PROJECT_MANAGER_AND_SALES] and not photo:
        raise HTTPException(status_code=400, detail="Shop photo is mandatory for Sales visits")

    parsed_date = None
    if visit_date:
        try:
            parsed_date = datetime.fromisoformat(visit_date.replace('Z', '+00:00'))
        except Exception:
            parsed_date = datetime.now(timezone.utc)

    try:
        status_enum = VisitStatus(status)
    except ValueError:
        status_enum = VisitStatus.SATISFIED

    visit_in = VisitCreate(
        shop_id=shop_id,
        visit_date=parsed_date,
        remarks=remarks,
        decline_remarks=decline_remarks,
        status=status_enum
    )

    service = VisitService()
    return await service.create_visit(visit_in, current_user, request, photo=photo)

@router.get("/", response_model=List[VisitRead])
async def read_visits(
    skip: int = 0,
    limit: int = 100,
    shop_id: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: User = Depends(read_access)
) -> Any:
    # If the user is Sales or Telesales, they can only view their own visits.
    if current_user and current_user.role in [UserRole.SALES, UserRole.TELESALES]:
        try:
            user_id = int(str(current_user.id))
        except:
            user_id = current_user.id
            
    service = VisitService()
    return await service.get_visits(skip, limit, current_user=current_user, user_id=user_id, shop_id=shop_id)

@router.patch("/{visit_id}", response_model=VisitRead)
async def update_visit(
    request: Request,
    visit_id: str,
    visit_in: VisitUpdate,
    current_user: User = Depends(create_access)
) -> Any:
    service = VisitService()
    return await service.update_visit(visit_id, visit_in, current_user, request)
