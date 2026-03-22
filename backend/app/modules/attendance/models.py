from beanie import Document
from typing import Optional
from datetime import datetime, date

class Attendance(Document):
    user_id: str
    date: Optional[date] = None
    punch_in: Optional[datetime] = None
    punch_out: Optional[datetime] = None
    total_hours: float = 0.0
    is_deleted: bool = False

    class Settings:
        name = "attendance"
