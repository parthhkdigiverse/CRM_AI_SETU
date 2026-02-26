from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.modules.todos.models import TodoStatus

class TodoBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[TodoStatus] = TodoStatus.PENDING

class TodoCreate(TodoBase):
    pass

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[TodoStatus] = None

class TodoRead(TodoBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
