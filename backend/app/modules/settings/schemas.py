from pydantic import BaseModel
from typing import Dict, Any, Optional

class SystemSettingsRead(BaseModel):
    id: int
    feature_flags: Dict[str, Any]
    access_policy: Dict[str, Any] = {}

    class Config:
        from_attributes = True

class SystemSettingsUpdate(BaseModel):
    feature_flags: Optional[Dict[str, Any]] = None
    access_policy: Optional[Dict[str, Any]] = None
