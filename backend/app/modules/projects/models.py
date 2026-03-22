from beanie import Document
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import field_validator
from app.core.enums import GlobalTaskStatus

_STATUS_MAP = {
    'PENDING': 'OPEN', 'NEW': 'OPEN', 'PLANNING': 'OPEN', 'SCHEDULED': 'OPEN',
    'ONGOING': 'IN_PROGRESS', 'CONTACTED': 'IN_PROGRESS', 'ACTIVE': 'IN_PROGRESS',
    'ON_HOLD': 'BLOCKED',
    'COMPLETED': 'RESOLVED', 'SOLVED': 'RESOLVED', 'DONE': 'RESOLVED',
}

class Project(Document):
    name: str
    description: Optional[str] = None
    client_id: Optional[str] = None
    pm_id: Optional[str] = None
    status: Optional[GlobalTaskStatus] = GlobalTaskStatus.OPEN
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: float = 0.0
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Enrichment fields (set by service, not stored in DB)
    total_issues: Optional[int] = 0
    resolved_issues: Optional[int] = 0
    progress_percentage: Optional[float] = 0.0
    client_name: Optional[str] = None
    pm_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    project_type: Optional[str] = None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        if v is None:
            return GlobalTaskStatus.OPEN
        if isinstance(v, str):
            if v in _STATUS_MAP:
                return _STATUS_MAP[v]
            # If it's a valid enum value, return it; otherwise default to OPEN
            try:
                return GlobalTaskStatus(v)
            except ValueError:
                return GlobalTaskStatus.OPEN
        return v

    @field_validator("created_at", "updated_at", "start_date", "end_date", mode="before")
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
        name = "projects"

