from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserRead, UserProfileUpdate

from app.modules.employees.schemas import EmployeeRoleUpdate
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from fastapi import Request
from pydantic import BaseModel

class UserStatusUpdate(BaseModel):
    is_active: bool

router = APIRouter()

admin_checker = RoleChecker([UserRole.ADMIN])

@router.get("/", response_model=List[UserRead])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    return db.query(User).filter(User.is_deleted == False).all()

@router.patch("/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: int,
    role_in: EmployeeRoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    old_role = user.role
    user.role = role_in.role
    db.commit()
    db.refresh(user)
    
    # Log Role Update
    activity_logger = ActivityLogger(db)
    await activity_logger.log_activity(
        user_id=current_user.id,
        user_role=current_user.role,
        action=ActionType.UPDATE,
        entity_type=EntityType.USER,
        entity_id=user.id,
        old_data={"role": old_role},
        new_data={"role": user.role},
        request=request
    )
    
    return user

@router.patch("/{user_id}/status", response_model=UserRead)
async def update_user_status(
    user_id: int,
    status_in: UserStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    old_status = user.is_active
    user.is_active = status_in.is_active
    db.commit()
    db.refresh(user)
    
    # Log Status Update
    activity_logger = ActivityLogger(db)
    await activity_logger.log_activity(
        user_id=current_user.id,
        user_role=current_user.role,
        action=ActionType.UPDATE,
        entity_type=EntityType.USER,
        entity_id=user.id,
        old_data={"is_active": old_status},
        new_data={"is_active": user.is_active},
        request=request
    )
    
    return user

@router.patch("/{user_id}/profile", response_model=UserRead)
async def admin_update_user_profile(
    user_id: int,
    profile_in: UserProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    old_name = user.name
    if profile_in.name is not None:
        user.name = profile_in.name
    if profile_in.phone is not None:
        user.phone = profile_in.phone
        
    db.commit()
    db.refresh(user)
    
    # Log Profile Update
    activity_logger = ActivityLogger(db)
    await activity_logger.log_activity(
        user_id=current_user.id,
        user_role=current_user.role,
        action=ActionType.UPDATE,
        entity_type=EntityType.USER,
        entity_id=user.id,
        old_data={"name": old_name},
        new_data={"name": user.name},
        request=request
    )
    
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    old_deleted_status = user.is_deleted
    user.is_deleted = True
    db.commit()
    db.refresh(user)
    
    # Log User Soft Deletion
    activity_logger = ActivityLogger(db)
    await activity_logger.log_activity(
        user_id=current_user.id,
        user_role=current_user.role,
        action=ActionType.DELETE,
        entity_type=EntityType.USER,
        entity_id=user_id,
        old_data={"is_deleted": old_deleted_status},
        new_data={"is_deleted": True},
        request=request
    )
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)