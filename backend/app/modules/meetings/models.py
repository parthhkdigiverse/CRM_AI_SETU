import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Enum, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

from app.core.database import Base

class MeetingType(str, enum.Enum):
    IN_PERSON = "In-Person"
    GOOGLE_MEET = "Google Meet"
    VIRTUAL = "Virtual"

class MeetingStatus(str, enum.Enum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    DONE = "DONE"
    CANCELLED = "CANCELLED"

class MeetingSummary(Base):
    __tablename__ = "meeting_summaries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    date = Column(DateTime, default=lambda: datetime.now(UTC))

    status = Column(Enum(MeetingStatus), default=MeetingStatus.SCHEDULED)
    meeting_type = Column(Enum(MeetingType), default=MeetingType.IN_PERSON)
    meet_link = Column(String, nullable=True)

    # --- New columns for real AI summary pipeline ---
    # Stores the Google Calendar Event ID to link back for transcript lookup
    calendar_event_id = Column(String, nullable=True, index=True)
    # Raw fetched transcript text from Google Drive
    transcript = Column(Text, nullable=True)
    # Structured AI summary: {"highlights": [...], "next_steps": "..."}
    ai_summary = Column(JSON, nullable=True)

    cancellation_reason = Column(Text, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    # Dedup flag: set True once the 15-min reminder notification is sent
    reminder_sent = Column(Boolean, default=False, nullable=False, server_default="false")
    todo_id = Column(Integer, ForeignKey("todos.id"), nullable=True)

    client = relationship("app.modules.clients.models.Client", backref="meeting_summaries")
    todo = relationship("app.modules.todos.models.Todo", backref="meeting")
