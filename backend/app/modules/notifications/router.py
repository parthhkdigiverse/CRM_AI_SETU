# backend/app/modules/notifications/router.py
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import NotificationRead

router = APIRouter()

@router.get("/", response_model=List[NotificationRead])
def read_notifications(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get all notifications for current user, newest first."""
    try:
        user_id = current_user.id if current_user else 0
        from app.modules.salary.models import AppSetting
        policy = db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
        
        query = db.query(Notification).filter(Notification.user_id == user_id)
        if not policy or policy.value == "SOFT":
            query = query.filter(Notification.is_deleted == False)
            
        return (
            query
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    except Exception as exc:
        import traceback
        print(f"[Notifications] Error fetching notifications: {exc}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notifications: {str(exc)}"
        )

@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """Returns the count of unread notifications — used by the bell badge."""
    user_id = current_user.id if current_user else 0
    from app.modules.salary.models import AppSetting
    policy = db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
    
    query = db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read == False)
    if not policy or policy.value == "SOFT":
        query = query.filter(Notification.is_deleted == False)
        
    count = query.count()
    return {"unread": count}

@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    user_id = current_user.id if current_user else 0
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification

@router.post("/mark-all-read")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """Mark all of the current user's notifications as read."""
    user_id = current_user.id if current_user else 0
    db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False  # noqa: E712
    ).update({"is_read": True})
    db.commit()
    return {"status": "ok"}

@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    user_id = current_user.id if current_user else 0
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    from app.modules.salary.models import AppSetting
    policy = db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
    is_hard = policy and policy.value == "HARD"

    if is_hard:
        db.delete(notification)
    else:
        notification.is_deleted = True
    db.commit()
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)
