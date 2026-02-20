from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserRead
from app.modules.employees.schemas import EmployeeRoleUpdate

router = APIRouter()

admin_checker = RoleChecker([UserRole.ADMIN])

@router.patch("/{user_id}/role", response_model=UserRead)
def update_user_role(
    user_id: int,
    role_in: EmployeeRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.role = role_in.role
    db.commit()
    db.refresh(user)
    
    return user