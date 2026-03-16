# backend/app/modules/timetable/models.py
from sqlalchemy import Column, Integer, String, Date, Time, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class TimetableEvent(Base):
    __tablename__ = "timetable_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    title = Column(String, nullable=False)
    assignee_name = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    location = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False, index=True)

    # Relationship to user
    user = relationship("app.modules.users.models.User", backref="timetable_events")
