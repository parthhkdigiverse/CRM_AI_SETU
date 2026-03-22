from beanie import Document
from typing import Optional
from datetime import datetime, timezone
import enum

class VisitStatus(str, enum.Enum):
    SATISFIED          = "SATISFIED"
    ACCEPT             = "ACCEPT"
    DECLINE            = "DECLINE"
    MISSED             = "MISSED"
    TAKE_TIME_TO_THINK = "TAKE_TIME_TO_THINK"
    OTHER              = "OTHER"
    COMPLETED          = "COMPLETED"
    CANCELLED          = "CANCELLED"
    SCHEDULED          = "SCHEDULED"

class Visit(Document):
    shop_id: str
    user_id: str
    status: VisitStatus = VisitStatus.SATISFIED
    remarks: Optional[str] = None
    decline_remarks: Optional[str] = None
    visit_date: datetime = datetime.now(timezone.utc)
    photo_url: Optional[str] = None
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)
    is_deleted: bool = False

    class Settings:
        name = "visits"
