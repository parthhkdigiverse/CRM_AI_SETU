from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, Float
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, default=lambda: datetime.now().date())
    punch_in = Column(DateTime, nullable=True)
    punch_out = Column(DateTime, nullable=True)
    total_hours = Column(Float, default=0.0)

    user = relationship("User", backref="attendance_records")
