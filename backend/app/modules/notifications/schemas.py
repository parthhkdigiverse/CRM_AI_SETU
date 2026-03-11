# backend/app/modules/notifications/schemas.py
from pydantic import BaseModel, ConfigDict, field_serializer
from datetime import datetime, timezone
from typing import Optional

class NotificationRead(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    is_read: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('created_at')
    def serialize_created_at(self, v: Optional[datetime]) -> Optional[str]:
        """
        Ensure created_at is always emitted as a UTC ISO-8601 string with a 'Z' suffix.
        Handles both naive datetimes (old rows before migration) and timezone-aware ones.
        """
        if v is None:
            return None
        if v.tzinfo is None:
            # Old naive row — was stored in UTC by the Python default; treat it as UTC
            v = v.replace(tzinfo=timezone.utc)
        else:
            v = v.astimezone(timezone.utc)
        return v.strftime('%Y-%m-%dT%H:%M:%SZ')
