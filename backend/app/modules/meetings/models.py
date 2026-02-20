import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class MeetingStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class MeetingSummary(Base):
    __tablename__ = "meeting_summaries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(MeetingStatus), default=MeetingStatus.SCHEDULED)
    cancellation_reason = Column(Text, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    project = relationship("app.modules.projects.models.Project", back_populates="meeting_summaries")
