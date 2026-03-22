from beanie import Document
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import field_validator

class Notification(Document):
    user_id: str
    title: str
    message: str
    is_read: bool = False
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> Any:
        if isinstance(v, str):
            for fmt in ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
        return v

    class Settings:
        name = "notifications"
