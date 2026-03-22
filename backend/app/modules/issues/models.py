from beanie import Document
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import field_validator
from app.core.enums import GlobalTaskStatus
import enum

class IssueSeverity(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

_STATUS_MAP = {
    'PENDING': 'OPEN', 'NEW': 'OPEN', 'PLANNING': 'OPEN', 'SCHEDULED': 'OPEN',
    'ONGOING': 'IN_PROGRESS', 'CONTACTED': 'IN_PROGRESS',
    'ON_HOLD': 'BLOCKED',
    'COMPLETED': 'RESOLVED', 'SOLVED': 'RESOLVED', 'DONE': 'RESOLVED',
}

class Issue(Document):
    title: str
    description: Optional[str] = None
    status: GlobalTaskStatus = GlobalTaskStatus.OPEN
    severity: str = IssueSeverity.MEDIUM
    remarks: Optional[str] = None
    is_deleted: bool = False
    opened_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    client_id: str
    project_id: Optional[str] = None
    reporter_id: str
    assigned_to_id: Optional[str] = None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        if isinstance(v, str) and v in _STATUS_MAP:
            return _STATUS_MAP[v]
        return v

    @field_validator("created_at", "updated_at", "opened_at", mode="before")
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
        name = "issues"

