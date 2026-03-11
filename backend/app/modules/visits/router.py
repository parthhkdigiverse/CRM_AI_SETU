# backend/app/modules/visits/router.py
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, status as http_status, Request, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.visits.schemas import VisitCreate, VisitRead, VisitUpdate, VisitStatus
from app.modules.visits.service import VisitService
import json

router = APIRouter()

# Role Access
create_access = RoleChecker([UserRole.SALES, UserRole.TELESALES, UserRole.ADMIN])
read_access = RoleChecker([UserRole.SALES, UserRole.TELESALES, UserRole.ADMIN, UserRole.PROJECT_MANAGER])

@router.post("/", response_model=VisitRead, status_code=http_status.HTTP_201_CREATED)
async def create_visit(
    request: Request,
    shop_id: int = Form(...),
    remarks: str = Form(...),
    status: str = Form(...),
    visit_date: Optional[str] = Form(None),
    decline_remarks: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(create_access)
) -> Any:
    """
    Create a visit. Accepts multipart/form-data (required for photo upload).
    """
    if current_user.role in [UserRole.SALES, UserRole.PROJECT_MANAGER_AND_SALES] and not photo:
        raise HTTPException(status_code=400, detail="Shop photo is mandatory for Sales visits")

    # Parse visit_date string → datetime
    from datetime import datetime, UTC
    parsed_date = None
    if visit_date:
        try:
            parsed_date = datetime.fromisoformat(visit_date.replace('Z', '+00:00'))
        except Exception:
            parsed_date = datetime.now(UTC)

    # Convert status string → enum (with fallback)
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

    service = VisitService(db)
    return await service.create_visit(visit_in, current_user, request, photo=photo)

@router.get("/", response_model=List[VisitRead])
def read_visits(
    skip: int = 0,
    limit: int = 100,
    shop_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(read_access)
) -> Any:
    service = VisitService(db)
    return service.get_visits(skip, limit, current_user=current_user, shop_id=shop_id)

@router.patch("/{visit_id}", response_model=VisitRead)
async def update_visit(
    request: Request,
    visit_id: int,
    visit_in: VisitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(create_access)
) -> Any:
    service = VisitService(db)
    return await service.update_visit(visit_id, visit_in, current_user, request)
