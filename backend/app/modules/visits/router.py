from typing import List, Any, Optional
from fastapi import APIRouter, Depends, status, Request, UploadFile, File, Form
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

@router.post("/", response_model=VisitRead, status_code=status.HTTP_201_CREATED)
async def create_visit(
    request: Request,
    shop_id: int = Form(...),
    visit_date: Optional[str] = Form(None), # Parse string to datetime
    remarks: Optional[str] = Form(None),
    decline_remarks: Optional[str] = Form(None),
    status: VisitStatus = Form(VisitStatus.SATISFIED),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(create_access)
) -> Any:
    """
    Create a visit. Supports photo upload.
    Note: Using Form data because of File upload.
    """
    if current_user.role in [UserRole.SALES, UserRole.PROJECT_MANAGER_AND_SALES] and not photo:
        raise HTTPException(status_code=400, detail="Shop photo is mandatory for Sales visits")
    from datetime import datetime, UTC

    
    parsed_date = None
    if visit_date:
        try:
            parsed_date = datetime.fromisoformat(visit_date.replace('Z', '+00:00'))
        except:
            parsed_date = datetime.now(UTC) # Fallback or error?

            
    visit_in = VisitCreate(
        shop_id=shop_id,
        visit_date=parsed_date,
        remarks=remarks,
        decline_remarks=decline_remarks,
        status=status
    )

    
    service = VisitService(db)
    return await service.create_visit(visit_in, current_user, request, photo)

@router.get("/", response_model=List[VisitRead])
def read_visits(
    skip: int = 0,
    limit: int = 100,
    shop_id: Optional[int] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(read_access) 
) -> Any:
    service = VisitService(db)
    return service.get_visits(skip, limit, user_id=user_id, shop_id=shop_id)

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
