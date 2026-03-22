from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from app.core.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import NotificationRead

router = APIRouter()

@router.get("/", response_model=List[NotificationRead])
async def read_notifications(skip: int = 0, limit: int = 100, current_user: User = Depends(get_current_user)) -> Any:
    try:
        from app.modules.salary.models import AppSetting
        user_id = current_user.id if current_user else 0
        policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
        query_filter = [Notification.user_id == user_id]
        if not policy or policy.value == "SOFT":
            query_filter.append(Notification.is_deleted != True)
        return await Notification.find(*query_filter).sort(-Notification.created_at).skip(skip).limit(limit).to_list()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch notifications: {str(exc)}")

@router.get("/unread-count")
async def get_unread_count(current_user: User = Depends(get_current_user)) -> dict:
    from app.modules.salary.models import AppSetting
    user_id = current_user.id if current_user else 0
    policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
    query_filter = [Notification.user_id == user_id, Notification.is_read == False]
    if not policy or policy.value == "SOFT":
        query_filter.append(Notification.is_deleted != True)
    count = await Notification.find(*query_filter).count()
    return {"unread": count}

@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_as_read(notification_id: str, current_user: User = Depends(get_current_user)) -> Any:
    user_id = current_user.id if current_user else 0
    notification = await Notification.find_one(Notification.id == notification_id, Notification.user_id == user_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    await notification.save()
    return notification

@router.post("/mark-all-read")
async def mark_all_read(current_user: User = Depends(get_current_user)) -> dict:
    user_id = current_user.id if current_user else 0
    notifications = await Notification.find(Notification.user_id == user_id, Notification.is_read == False).to_list()
    for notif in notifications:
        notif.is_read = True
        await notif.save()
    return {"status": "ok"}

@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(notification_id: str, current_user: User = Depends(get_current_user)) -> None:
    from app.modules.salary.models import AppSetting
    user_id = current_user.id if current_user else 0
    notification = await Notification.find_one(Notification.id == notification_id, Notification.user_id == user_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
    if policy and policy.value == "HARD":
        await notification.delete()
    else:
        notification.is_deleted = True
        await notification.save()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
