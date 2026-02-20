from typing import List, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.areas.schemas import AreaCreate, AreaRead, AreaAssign
from app.modules.areas.service import AreaService

router = APIRouter()

# Role Checker
admin_access = RoleChecker([UserRole.ADMIN])

@router.post("/", response_model=AreaRead, status_code=status.HTTP_201_CREATED)
def create_area(
    area_in: AreaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_access)
) -> Any:
    """
    Create a new Area. Admin only.
    """
    service = AreaService(db)
    return service.create_area(area_in)

@router.get("/", response_model=List[AreaRead])
def read_areas(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_access) # Admin usually manages areas
) -> Any:
    service = AreaService(db)
    return service.get_areas(skip, limit)

@router.patch("/{area_id}/assign", response_model=AreaRead)
def assign_area(
    area_id: int,
    assign_in: AreaAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_access)
) -> Any:
    """
    Assign an area to a user. Admin only.
    """
    service = AreaService(db)
    return service.assign_area(area_id, assign_in.assigned_user_id)
