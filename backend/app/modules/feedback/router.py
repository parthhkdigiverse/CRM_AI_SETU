from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker, get_current_user
from app.modules.users.models import User, UserRole
from app.modules.clients.models import Client
from app.modules.feedback.models import Feedback, UserFeedback
from app.modules.feedback.schemas import FeedbackCreate, FeedbackRead, UserFeedbackCreate, UserFeedbackRead

router = APIRouter()

# Role definitions for viewing feedback
staff_checker = RoleChecker([
    UserRole.ADMIN, 
    UserRole.SALES, 
    UserRole.TELESALES, 
    UserRole.PROJECT_MANAGER, 
    UserRole.PROJECT_MANAGER_AND_SALES
])

@router.post("/{client_id}/feedback", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def create_feedback(
    client_id: int,
    feedback_in: FeedbackCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Submit feedback for a client. Public endpoint.
    """
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Validate rating
    if not (1 <= feedback_in.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    dump = feedback_in.model_dump()
    if "client_id" in dump:
        del dump["client_id"]

    db_feedback = Feedback(
        **dump,
        client_id=client_id
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

@router.get("/{client_id}/feedback", response_model=List[FeedbackRead])
def read_client_feedback(
    client_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    if current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    offset = (page - 1) * limit
    feedbacks = db.query(Feedback).filter(Feedback.client_id == client_id)\
        .order_by(Feedback.created_at.desc())\
        .offset(offset).limit(limit).all()
        
    return feedbacks


# --- Internal User Feedback Endpoints ---

@router.post("/user", response_model=UserFeedbackRead, status_code=status.HTTP_201_CREATED)
def create_user_feedback(
    feedback_in: UserFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Submit feedback/issue about the system (Internal).
    """
    db_feedback = UserFeedback(
        user_id=current_user.id,
        subject=feedback_in.subject,
        message=feedback_in.message
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

@router.get("/user", response_model=List[UserFeedbackRead])
def read_user_feedbacks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Retrieve system feedback. Admins see all, users see their own.
    """
    query = db.query(UserFeedback)
    
    if current_user.role != UserRole.ADMIN:
        query = query.filter(UserFeedback.user_id == current_user.id)
        
    return query.order_by(UserFeedback.created_at.desc()).offset(skip).limit(limit).all()

