from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from app.modules.activity_logs.models import ActionType, EntityType

class ActivityLogBase(BaseModel):
    user_id: int
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
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
