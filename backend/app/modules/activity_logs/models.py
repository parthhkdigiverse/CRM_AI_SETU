from beanie import Document
from typing import Optional, Any, Dict
from datetime import datetime
import enum

class ActionType(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    ASSIGN = "ASSIGN"
    UNASSIGN = "UNASSIGN"
    STATUS_CHANGE = "STATUS_CHANGE"
    RESCHEDULE = "RESCHEDULE"
    CANCEL = "CANCEL"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"

class EntityType(str, enum.Enum):
    CLIENT = "CLIENT"
    PROJECT = "PROJECT"
    ISSUE = "ISSUE"
    MEETING = "MEETING"
    LEAD = "LEAD"
    VISIT = "VISIT"
    REASSIGN = "REASSIGN"
    FEEDBACK = "FEEDBACK"
    USER = "USER"

class ActivityLog(Document):
    user_id: str
    user_role: str
    action: str
    entity_type: str
    entity_id: str
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime = datetime.utcnow()

    class Settings:
        name = "activity_logs"
