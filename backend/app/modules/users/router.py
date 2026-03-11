# backend/app/modules/users/router.py
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker, get_current_active_user
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserRead, UserProfileUpdate
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from fastapi import Request
from pydantic import BaseModel
import uuid
from datetime import date as dt_date

class UserStatusUpdate(BaseModel):
    is_active: bool

class UserRoleUpdate(BaseModel):
    role: UserRole

router = APIRouter()

admin_checker = RoleChecker([UserRole.ADMIN])

@router.get("/", response_model=List[UserRead])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    return db.query(User).filter(User.is_deleted != True).all()

@router.patch("/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: int,
    role_in: UserRoleUpdate,
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

    activity_logger = ActivityLogger(db)
    await activity_logger.log_activity(
        user_id=current_user.id if current_user else 0,
        user_role=current_user.role if current_user else UserRole.ADMIN,
        action=ActionType.UPDATE,
        entity_type=EntityType.USER,
        entity_id=user.id,
        old_data={"role": old_role},
        new_data={"role": user.role},
        request=request
    )

    return user

@router.patch("/{user_id}/status", response_model=UserRead)
async def update_user_status(
    user_id: int,
    status_in: UserStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_status = user.is_active
    user.is_active = status_in.is_active
    db.commit()
    db.refresh(user)

    activity_logger = ActivityLogger(db)
    await activity_logger.log_activity(
        user_id=current_user.id if current_user else 0,
        user_role=current_user.role if current_user else UserRole.ADMIN,
        action=ActionType.UPDATE,
        entity_type=EntityType.USER,
        entity_id=user.id,
        old_data={"is_active": old_status},
        new_data={"is_active": user.is_active},
        request=request
    )

    return user

@router.patch("/{user_id}/profile", response_model=UserRead)
async def admin_update_user_profile(
    user_id: int,
    profile_in: UserProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_name = user.name
    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    activity_logger = ActivityLogger(db)
    await activity_logger.log_activity(
        user_id=current_user.id if current_user else 0,
        user_role=current_user.role if current_user else UserRole.ADMIN,
        action=ActionType.UPDATE,
        entity_type=EntityType.USER,
        entity_id=user.id,
        old_data={"name": old_name},
        new_data={"name": user.name},
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

    old_deleted_status = user.is_deleted
    user.is_deleted = True
    db.commit()
    db.refresh(user)

    activity_logger = ActivityLogger(db)
    await activity_logger.log_activity(
        user_id=current_user.id if current_user else 0,
        user_role=current_user.role if current_user else UserRole.ADMIN,
        action=ActionType.DELETE,
        entity_type=EntityType.USER,
        entity_id=user_id,
        old_data={"is_deleted": old_deleted_status},
        new_data={"is_deleted": True},
        request=request
    )
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/batch-delete")
async def batch_delete_users(
    ids: List[int],
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    try:
        # Soft delete
        db.query(User).filter(User.id.in_(ids)).update({"is_deleted": True}, synchronize_session=False)
        db.commit()
        
        activity_logger = ActivityLogger(db)
        # Log collectively or individually? Collectively is faster.
        await activity_logger.log_activity(
            user_id=current_user.id if current_user else 0,
            user_role=current_user.role if current_user else UserRole.ADMIN,
            action=ActionType.DELETE,
            entity_type=EntityType.USER,
            entity_id=0, # 0 for batch
            old_data={"batch_ids": ids},
            new_data={"is_deleted": True},
            request=request
        )
        return {"message": f"Successfully deleted {len(ids)} users"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ── Referral Code endpoints (moved from employees router) ─────────────────────

@router.post("/{user_id}/referral-code")
def generate_referral_code(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    allowed_roles = [UserRole.SALES, UserRole.TELESALES]
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Referral codes can only be generated for SALES or TELESALES roles"
        )

    if user.referral_code:
        return {"user_id": user.id, "code": user.referral_code}

    code = f"REF-{user.id}-{str(uuid.uuid4())[:8].upper()}"
    existing = db.query(User).filter(User.referral_code == code, User.id != user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Referral code collision; try again")

    user.referral_code = code
    db.commit()
    db.refresh(user)
    return {"user_id": user.id, "code": user.referral_code}

@router.get("/{user_id}/referral-code")
def get_referral_code(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.referral_code:
        raise HTTPException(status_code=404, detail="Referral code not set for this user")
    return {"user_id": user.id, "code": user.referral_code}

# ── PM Availability endpoint (moved from employees router) ────────────────────

from sqlalchemy import cast, Date
from app.modules.meetings.models import MeetingSummary
from app.modules.clients.models import Client

@router.get("/{pm_id}/availability")
def get_pm_availability(
    pm_id: int,
    date: dt_date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    pm = db.query(User).filter(
        User.id == pm_id,
        User.role.in_([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])
    ).first()
    if not pm:
        raise HTTPException(status_code=404, detail="Project Manager not found")

    meetings = db.query(MeetingSummary).join(Client).filter(
        Client.pm_id == pm_id,
        cast(MeetingSummary.date, Date) == date,
        MeetingSummary.status != "CANCELLED"
    ).all()

    booked_hours = [m.date.hour for m in meetings]
    free_slots = [f"{h:02d}:00" for h in range(9, 18) if h not in booked_hours]

    return {"pm_id": pm_id, "date": date, "free_slots": free_slots}
