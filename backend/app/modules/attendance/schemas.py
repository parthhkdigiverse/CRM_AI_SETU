# backend/app/modules/attendance/schemas.py
from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List

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

class AttendanceLog(BaseModel):
    id: int
    punch_in: Optional[datetime] = None
    punch_out: Optional[datetime] = None
    total_hours: float = 0.0

    class Config:
        from_attributes = True

class PunchStatus(BaseModel):
    is_punched_in: bool
    last_punch: Optional[datetime] = None
    last_punch_ts: Optional[float] = None  # Epoch milliseconds
    first_punch_in: Optional[datetime] = None
    first_punch_in_ts: Optional[float] = None  # Epoch milliseconds
    today_hours: float = 0.0
    week_hours: float = 0.0
    month_hours: float = 0.0


class AttendanceDaySummary(BaseModel):
    date: date
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    first_punch_in: Optional[datetime] = None
    last_punch_out: Optional[datetime] = None
    total_hours: float = 0.0
    day_status: str = "PRESENT"  # PRESENT | HALF | ABSENT | OFF
    leave_status: Optional[str] = None


class AttendanceSummaryResponse(BaseModel):
    start_date: date
    end_date: date
    total_hours: float = 0.0
    records: List[AttendanceDaySummary]


class AttendanceSettings(BaseModel):
    absent_hours_threshold: float = 0.0
    half_day_hours_threshold: float = 4.0
    weekly_off_saturday: str = "FULL"  # NONE | HALF | FULL
    weekly_off_sunday: str = "FULL"  # NONE | HALF | FULL
    official_holidays: List[date] = []
