from typing import Optional, Annotated
from datetime import date, time
from beanie import Document, Indexed
from pydantic import Field

class TimetableEvent(Document):
    user_id: str  # MongoDB ma User ni ID string/ObjectId tarike
    
    title: str
    assignee_name: Optional[str] = None
    date: date
    start_time: time
    end_time: time
    location: Optional[str] = None
    is_deleted: Annotated[bool, Indexed()] = False

    class Settings:
        name = "timetable_events"  # MongoDB collection nu naam

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "60d5ecb8b39d880015f5a123",
                "title": "Client Visit",
                "date": "2026-03-20",
                "start_time": "10:00:00",
                "end_time": "11:00:00",
                "location": "Surat"
            }
        }