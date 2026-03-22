from typing import Optional
from datetime import datetime, time, timezone
import enum
from beanie import Document, Indexed
from pydantic import Field

class TodoStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class TodoPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class Todo(Document):
    user_id: str  # MongoDB ma ID hamesha string/ObjectId hoy chhe
    title: str = Indexed()
    description: Optional[str] = None
    
    due_date: Optional[datetime] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    
    status: TodoStatus = TodoStatus.PENDING
    priority: TodoPriority = TodoPriority.MEDIUM
    
    assigned_to: Optional[str] = None
    related_entity: Optional[str] = None
    evidence_url: Optional[str] = None
    is_deleted: bool = Indexed(default=False)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    client_id: Optional[str] = None

    class Settings:
        name = "todos"  # Aa MongoDB na collection nu naam chhe

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "60d5ecb8b39d880015f5a123",
                "title": "Meeting with Client",
                "status": "PENDING",
                "priority": "HIGH"
            }
        }