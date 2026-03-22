from beanie import PydanticObjectId
# backend/app/modules/activity_logs/schemas.py
from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime
from app.modules.activity_logs.models import ActionType, EntityType

class ActivityLogBase(BaseModel):
    user_id: str
    user_role: str
    action: ActionType
    entity_type: EntityType
    entity_id: int
    old_data: Optional[Any] = None
    new_data: Optional[Any] = None
    ip_address: Optional[str] = None

class ActivityLogCreate(ActivityLogBase):
    pass

class ActivityLogResponse(ActivityLogBase):
    id: Optional[PydanticObjectId] = None
    created_at: datetime
    user_name: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True

