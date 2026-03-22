from beanie import Document
from typing import Optional, Any, Dict
from datetime import datetime, timezone
from pydantic import field_validator
from app.core.enums import GlobalTaskStatus
import enum

class MeetingType(str, enum.Enum):
    IN_PERSON = "In-Person"
    GOOGLE_MEET = "Google Meet"
    VIRTUAL = "Virtual"

_STATUS_MAP = {
    'PENDING': 'OPEN', 'NEW': 'OPEN', 'PLANNING': 'OPEN', 'SCHEDULED': 'OPEN',
    'ONGOING': 'IN_PROGRESS', 'CONTACTED': 'IN_PROGRESS', 'ACTIVE': 'IN_PROGRESS',
    'ON_HOLD': 'BLOCKED',
    'COMPLETED': 'RESOLVED', 'SOLVED': 'RESOLVED', 'DONE': 'RESOLVED',
}

_MEETING_TYPE_MAP = {
    'IN_PERSON': 'In-Person', 'IN-PERSON': 'In-Person', 'in_person': 'In-Person',
    'GOOGLE_MEET': 'Google Meet', 'google_meet': 'Google Meet',
    'VIRTUAL': 'Virtual', 'virtual': 'Virtual',
}

class MeetingSummary(Document):
    title: Optional[str] = None
    content: Optional[str] = None
    date: Optional[datetime] = None
    status: Optional[GlobalTaskStatus] = GlobalTaskStatus.OPEN
    meeting_type: Optional[MeetingType] = MeetingType.IN_PERSON
    meet_link: Optional[str] = None
    calendar_event_id: Optional[str] = None
    transcript: Optional[str] = None
    ai_summary: Optional[Dict[str, Any]] = None
    cancellation_reason: Optional[str] = None
    client_id: Optional[str] = None
    is_deleted: bool = False
    reminder_sent: bool = False
    todo_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        if v is None:
            return GlobalTaskStatus.OPEN
        if isinstance(v, str) and v in _STATUS_MAP:
            return _STATUS_MAP[v]
        return v

    @field_validator("meeting_type", mode="before")
    @classmethod
    def normalize_meeting_type(cls, v: Any) -> Any:
        if v is None:
            return MeetingType.IN_PERSON
        if isinstance(v, str) and v in _MEETING_TYPE_MAP:
            return _MEETING_TYPE_MAP[v]
        return v

    @field_validator("date", "created_at", "updated_at", mode="before")
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
        name = "meetingSummaries"

