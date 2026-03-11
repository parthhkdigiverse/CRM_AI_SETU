# backend/app/modules/todos/models.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, Boolean, Time
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

import enum
from app.core.database import Base

class TodoStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class TodoPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    due_date = Column(DateTime, nullable=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    status = Column(Enum(TodoStatus), default=TodoStatus.PENDING)
    priority = Column(Enum(TodoPriority), default=TodoPriority.MEDIUM)
    assigned_to = Column(String, nullable=True)
    related_entity = Column(String, nullable=True)
    evidence_url = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)


    # Relationship
    user = relationship("app.modules.users.models.User", backref="todos")
    client = relationship("app.modules.clients.models.Client", backref="todos")
