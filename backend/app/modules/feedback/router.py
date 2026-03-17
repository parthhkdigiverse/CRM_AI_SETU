# backend/app/modules/feedback/router.py
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

admin_checker = RoleChecker([UserRole.ADMIN])

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
    from app.modules.salary.models import AppSetting
    policy = db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()

    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted == False).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role != UserRole.ADMIN:
        has_access = (
            client.owner_id == current_user.id
            or client.pm_id == current_user.id
            or client.referred_by_id == current_user.id
        )
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")

    service = FeedbackService(db)
    feedbacks = service.get_client_feedbacks(client_id)
    if not policy or policy.value == "SOFT":
        feedbacks = [f for f in feedbacks if not getattr(f, 'is_deleted', False)]
    return feedbacks


@router.get("/feedbacks/all", response_model=List[FeedbackRead])
def read_all_client_feedbacks(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    q = db.query(Feedback).join(Client, Feedback.client_id == Client.id, isouter=True)
    if current_user.role != UserRole.ADMIN:
        q = q.filter(
            (Client.owner_id == current_user.id)
            | (Client.pm_id == current_user.id)
            | (Client.referred_by_id == current_user.id)
        )
    from app.modules.salary.models import AppSetting
    policy = db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
    if not policy or policy.value == "SOFT":
        q = q.filter(Feedback.is_deleted == False)
    return q.order_by(Feedback.created_at.desc()).all()

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
    from app.modules.salary.models import AppSetting
    policy = db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
    service = FeedbackService(db)
    
    feedbacks = service.get_user_feedbacks()
    if not policy or policy.value == "SOFT":
        feedbacks = [f for f in feedbacks if not getattr(f, 'is_deleted', False)]
        
    if current_user and current_user.role == UserRole.ADMIN:
        return feedbacks
    else:
        user_id = current_user.id if current_user else 0
        return [f for f in feedbacks if f.user_id == user_id]

@router.delete("/client/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> None:
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
        
    from app.modules.salary.models import AppSetting
    policy = db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
    is_hard = policy and policy.value == "HARD"

    if is_hard:
        db.delete(feedback)
    else:
        feedback.is_deleted = True
    db.commit()
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.delete("/user/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> None:
    feedback = db.query(UserFeedback).filter(UserFeedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="User feedback not found")
        
    from app.modules.salary.models import AppSetting
    policy = db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
    is_hard = policy and policy.value == "HARD"

    if is_hard:
        db.delete(feedback)
    else:
        feedback.is_deleted = True
    db.commit()
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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

