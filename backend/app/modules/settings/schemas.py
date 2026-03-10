from pydantic import BaseModel
from typing import Dict, Any

class SystemSettingsRead(BaseModel):
    id: int
    feature_flags: Dict[str, Any]

    class Config:
        from_attributes = True

class SystemSettingsUpdate(BaseModel):
    feature_flags: Dict[str, Any]
