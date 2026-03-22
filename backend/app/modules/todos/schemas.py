from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, time
from beanie import PydanticObjectId
from app.modules.todos.models import TodoStatus, TodoPriority

class TodoBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[TodoStatus] = TodoStatus.PENDING
    priority: Optional[TodoPriority] = TodoPriority.MEDIUM
    assigned_to: Optional[str] = None
    related_entity: Optional[str] = None
    evidence_url: Optional[str] = None
    client_id: Optional[str] = None  # Integer ne badle String karyu

class TodoCreate(TodoBase):
    pass

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[TodoStatus] = None
    priority: Optional[TodoPriority] = None
    assigned_to: Optional[str] = None
    related_entity: Optional[str] = None
    evidence_url: Optional[str] = None
    client_id: Optional[str] = None

class TodoRead(TodoBase):
    id: PydanticObjectId = Field(alias="_id") # MongoDB ni internal ID mate
    user_id: str | int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True # PydanticObjectId mate jaruri che
    )