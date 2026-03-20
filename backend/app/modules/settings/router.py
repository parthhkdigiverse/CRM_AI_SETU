# backend/app/modules/settings/router.py
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker, get_current_user
from app.modules.users.models import User, UserRole
from app.modules.settings.models import SystemSettings
from app.modules.settings.schemas import SystemSettingsRead, SystemSettingsUpdate

router = APIRouter()
admin_access = RoleChecker([UserRole.ADMIN])

@router.get("/", response_model=SystemSettingsRead)
def get_settings(
    db: Session = Depends(get_db),
    # Require authentication using get_current_user
    current_user: User = Depends(get_current_user)
) -> Any:
    # Get or create the single settings row
    settings_obj = db.query(SystemSettings).first()
    if not settings_obj:
        settings_obj = SystemSettings(feature_flags={"enable_soft_delete": True})
        db.add(settings_obj)
        db.commit()
        db.refresh(settings_obj)
    return settings_obj

@router.patch("/", response_model=SystemSettingsRead)
def update_settings(
    settings_in: SystemSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_access)
) -> Any:
    """Update global system settings (Admin only)."""
    settings_obj = db.query(SystemSettings).first()
    if not settings_obj:
        settings_obj = SystemSettings(feature_flags={"enable_soft_delete": True})
        db.add(settings_obj)
    
    if settings_in.feature_flags is not None:
        current_flags = settings_obj.feature_flags or {}
        settings_obj.feature_flags = {**current_flags, **settings_in.feature_flags}
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(settings_obj, "feature_flags")
    
    if settings_in.access_policy is not None:
        settings_obj.access_policy = settings_in.access_policy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(settings_obj, "access_policy")
    
    db.commit()
    db.refresh(settings_obj)
    return settings_obj

@router.get("/access-control")
def get_access_control(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    settings_obj = db.query(SystemSettings).first()
    if not settings_obj:
        return {"page_access": {}, "feature_access": {}}
    return settings_obj.access_policy or {}

@router.post("/access-control")
def set_access_control(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_access)
):
    settings_obj = db.query(SystemSettings).first()
    if not settings_obj:
        settings_obj = SystemSettings(feature_flags={}, access_policy={})
        db.add(settings_obj)
    
    settings_obj.access_policy = data
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(settings_obj, "access_policy")
    db.commit()
    db.refresh(settings_obj)
    return JSONResponse(content=data)
