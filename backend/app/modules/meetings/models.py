# backend/app/modules/meetings/models.py
import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Enum, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

from app.core.database import Base
from app.core.enums import GlobalTaskStatus


class MeetingType(str, enum.Enum):
    IN_PERSON   = "In-Person"
    GOOGLE_MEET = "Google Meet"
    VIRTUAL     = "Virtual"


class MeetingSummary(Base):
    __tablename__ = "meeting_summaries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    date = Column(DateTime, default=lambda: datetime.now(UTC))

    status = Column(Enum(GlobalTaskStatus), default=GlobalTaskStatus.OPEN)
    meeting_type = Column(Enum(MeetingType), default=MeetingType.IN_PERSON)
    meet_link = Column(String, nullable=True)

    # Google Calendar / AI summary pipeline
    calendar_event_id = Column(String, nullable=True, index=True)
    transcript = Column(Text, nullable=True)
    ai_summary = Column(JSON, nullable=True)

    cancellation_reason = Column(Text, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    is_deleted = Column(Boolean, default=False, index=True)

    reminder_sent = Column(Boolean, default=False, nullable=False, server_default="false")
    todo_id = Column(Integer, ForeignKey("todos.id"), nullable=True)

    client = relationship("app.modules.clients.models.Client", backref="meeting_summaries")
    todo = relationship("app.modules.todos.models.Todo", backref="meeting")
