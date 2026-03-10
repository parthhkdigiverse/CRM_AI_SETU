from typing import List, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.areas.schemas import AreaCreate, AreaRead, AreaAssign, AreaUpdate
from app.modules.areas.service import AreaService

router = APIRouter()

# Role Checkers
admin_access = RoleChecker([UserRole.ADMIN])
staff_access = RoleChecker([
    UserRole.ADMIN, UserRole.SALES, UserRole.TELESALES,
    UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES
])

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

@router.patch("/{area_id}", response_model=AreaRead)
def update_area(
    area_id: int,
    area_in: AreaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_access)
) -> Any:
    """
    Update an existing Area's name, description, or coordinates. Admin only.
    """
    service = AreaService(db)
    return service.update_area(area_id, area_in)

@router.get("/archived", response_model=List[AreaRead])
def read_archived_areas(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access)
) -> Any:
    """
    Get all archived areas. Staff scope limited by permissions.
    """
    service = AreaService(db)
    return service.get_archived_areas(current_user)

@router.get("/", response_model=List[AreaRead])
def read_areas(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access)
) -> Any:
    service = AreaService(db)
    return service.get_areas(current_user, skip, limit)

@router.patch("/{area_id}/assign", response_model=AreaRead)
def assign_area(
    area_id: int,
    assign_in: AreaAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_access)
) -> Any:
    """
    Assign an area to users. Admin only.
    """
    service = AreaService(db)
    return service.assign_area(area_id, assign_in.user_ids, assign_in.shop_ids)

@router.delete("/{area_id}", status_code=status.HTTP_200_OK)
def archive_area(
    area_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access)
) -> Any:
    """
    Soft-delete (archive) an area and its shops. Available to staff.
    """
    service = AreaService(db)
    return service.archive_area(area_id, current_user)

@router.patch("/{area_id}/unarchive", response_model=AreaRead)
def unarchive_area(
    area_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access)
) -> Any:
    """
    Unarchive an area. Staff scope limited to owners/assignees.
    """
    service = AreaService(db)
    return service.unarchive_area(area_id, current_user)

@router.delete("/{area_id}/hard-delete", status_code=status.HTTP_200_OK)
def hard_delete_area(
    area_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_access)
) -> Any:
    """
    Permanently delete an area and all associated shops. Admin only.
    """
    service = AreaService(db)
    return service.hard_delete_area(area_id)
