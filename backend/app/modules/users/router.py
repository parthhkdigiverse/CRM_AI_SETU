from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserRead
from app.modules.employees.schemas import EmployeeRoleUpdate
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from fastapi import Request

router = APIRouter()

admin_checker = RoleChecker([UserRole.ADMIN])

@router.get("/", response_model=List[UserRead])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    return db.query(User).all()

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
        
    db.delete(user)
    db.commit()
    
    # Log User Deletion
    activity_logger = ActivityLogger(db)
    await activity_logger.log_activity(
        user_id=current_user.id,
        user_role=current_user.role,
        action=ActionType.DELETE,
        entity_type=EntityType.USER,
        entity_id=user_id,
        old_data={"email": user.email},
        new_data=None,
        request=request
    )
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)