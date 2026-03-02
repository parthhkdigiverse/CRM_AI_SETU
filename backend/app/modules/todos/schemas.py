from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.modules.todos.models import TodoStatus, TodoPriority

class TodoBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[TodoStatus] = TodoStatus.PENDING
    priority: Optional[TodoPriority] = TodoPriority.MEDIUM
    assigned_to: Optional[str] = None
    related_entity: Optional[str] = None
    evidence_url: Optional[str] = None

class TodoCreate(TodoBase):
    pass

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[TodoStatus] = None
    priority: Optional[TodoPriority] = None
    assigned_to: Optional[str] = None
    related_entity: Optional[str] = None
    evidence_url: Optional[str] = None

class TodoRead(TodoBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
