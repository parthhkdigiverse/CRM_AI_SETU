# backend/app/modules/activity_logs/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.schemas import ActivityLogResponse
from app.modules.users.models import User, UserRole

router = APIRouter()

@router.get("/", response_model=List[ActivityLogResponse])
def read_activity_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    allowed_roles = [UserRole.ADMIN, UserRole.SALES, UserRole.TELESALES, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]
    if current_user and current_user.role not in allowed_roles:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have enough privileges to view activity logs"
        )
    
    logger = ActivityLogger(db)
    return logger.get_logs(skip=skip, limit=limit)
