from typing import Any
from fastapi import APIRouter, Depends
from app.core.dependencies import RoleChecker, get_current_user
from app.modules.users.models import User, UserRole
from app.modules.settings.models import SystemSettings
from app.modules.settings.schemas import SystemSettingsRead, SystemSettingsUpdate

router = APIRouter()
admin_access = RoleChecker([UserRole.ADMIN])

@router.get("/", response_model=SystemSettingsRead)
async def get_settings(
    current_user: User = Depends(get_current_user)
) -> Any:
    # MongoDB ma pela settings object shodho
    settings_obj = await SystemSettings.find_one()
    
    if not settings_obj:
        # Jo na hoy to navu create karo
        settings_obj = SystemSettings(feature_flags={"enable_soft_delete": True})
        await settings_obj.insert()
        
    return settings_obj

@router.patch("/", response_model=SystemSettingsRead)
async def update_settings(
    settings_in: SystemSettingsUpdate,
    current_user: User = Depends(admin_access)
) -> Any:
    """Update global system settings (Admin only)."""
    settings_obj = await SystemSettings.find_one()
    
    if not settings_obj:
        settings_obj = SystemSettings(feature_flags={"enable_soft_delete": True})
        await settings_obj.insert()
    
    # Merge feature flags
    current_flags = settings_obj.feature_flags or {}
    new_flags = {**current_flags, **settings_in.feature_flags}
    
    # MongoDB update logic
    await settings_obj.set({"feature_flags": new_flags})
    
    return settings_obj