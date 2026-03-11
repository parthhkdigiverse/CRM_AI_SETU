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
global_router = APIRouter()

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
    from app.modules.feedback.service import FeedbackService
    service = FeedbackService(db)
    # Ensure client exists
    from app.modules.clients.models import Client
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    feedback_in.client_id = client_id
    return service.create_client_feedback(feedback_in)

@global_router.post("/public/submit", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def create_public_feedback(
    feedback_in: FeedbackCreate,
    db: Session = Depends(get_db)
) -> Any:
    """Public endpoint for submitting feedback via QR code scans."""
    from app.modules.feedback.service import FeedbackService
    service = FeedbackService(db)
    return service.create_client_feedback(feedback_in)

@global_router.get("/all", response_model=List[FeedbackRead])
def read_all_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """Admin endpoint to view all client feedback."""
    from app.modules.feedback.service import FeedbackService
    service = FeedbackService(db)
    return service.get_all_client_feedbacks()

@router.get("/{client_id}/feedback", response_model=List[FeedbackRead])
def read_client_feedback(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    from app.modules.feedback.service import FeedbackService
    service = FeedbackService(db)
    return service.get_client_feedbacks(client_id)

@router.post("/user", response_model=UserFeedbackRead, status_code=status.HTTP_201_CREATED)
def create_user_feedback(
    feedback_in: UserFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    from app.modules.feedback.service import FeedbackService
    service = FeedbackService(db)
    user_id = current_user.id if current_user else 0
    return service.create_user_feedback(user_id, feedback_in)

@router.get("/user", response_model=List[UserFeedbackRead])
def read_user_feedbacks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    from app.modules.feedback.service import FeedbackService
    service = FeedbackService(db)
    if current_user and current_user.role == UserRole.ADMIN:
        return service.get_user_feedbacks()
    else:
        user_id = current_user.id if current_user else 0
        return [f for f in service.get_user_feedbacks() if f.user_id == user_id]


@global_router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> None:
    """Delete a feedback record by ID. Accessible to all staff roles."""
    from app.modules.feedback.service import FeedbackService
    service = FeedbackService(db)
    try:
        service.delete_feedback(feedback_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Feedback not found")

