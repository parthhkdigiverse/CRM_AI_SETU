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
    if current_user.role != UserRole.ADMIN:
         raise HTTPException(
            status_code=status.HTTP_430_FORBIDDEN,
            detail="Only Admins can view activity logs"
        )
    
    logger = ActivityLogger(db)
    return logger.get_logs(skip=skip, limit=limit)
