from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.projects.models import Project
from app.modules.feedback.models import Feedback
from app.modules.feedback.schemas import FeedbackCreate, FeedbackRead

router = APIRouter()

# Role definitions for viewing feedback
staff_checker = RoleChecker([
    UserRole.ADMIN, 
    UserRole.SALES, 
    UserRole.TELESALES, 
    UserRole.PROJECT_MANAGER, 
    UserRole.PROJECT_MANAGER_AND_SALES
])

@router.post("/{project_id}/feedback", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def create_feedback(
    project_id: int,
    feedback_in: FeedbackCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Submit feedback for a project. Public endpoint.
    """
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate rating
    if not (1 <= feedback_in.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    db_feedback = Feedback(
        **feedback_in.model_dump(),
        project_id=project_id
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

@router.get("/{project_id}/feedback", response_model=List[FeedbackRead])
def read_project_feedback(
    project_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if current_user.role == UserRole.PROJECT_MANAGER and db_project.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    offset = (page - 1) * limit
    feedbacks = db.query(Feedback).filter(Feedback.project_id == project_id)\
        .order_by(Feedback.created_at.desc())\
        .offset(offset).limit(limit).all()
        
    return feedbacks
