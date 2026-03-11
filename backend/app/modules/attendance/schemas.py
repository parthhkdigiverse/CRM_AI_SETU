# backend/app/modules/attendance/schemas.py
from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional

class AttendanceBase(BaseModel):
    user_id: int
    date: date
    punch_in: Optional[datetime] = None
    punch_out: Optional[datetime] = None
    total_hours: float = 0.0

class AttendanceCreate(AttendanceBase):
    pass

class AttendanceResponse(AttendanceBase):
    id: int

    class Config:
        from_attributes = True

class PunchStatus(BaseModel):
    is_punched_in: bool
    last_punch: Optional[datetime] = None
    today_hours: float = 0.0
    week_hours: float = 0.0
    month_hours: float = 0.0
