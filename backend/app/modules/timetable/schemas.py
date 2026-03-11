# backend/app/modules/timetable/schemas.py
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date, time

class TimelineEvent(BaseModel):
    id: int
    title: str
    date: str # YYYY-MM-DD
    user: str # Assignee/User name
    sh: Optional[int] = None
    sm: Optional[int] = None
    eh: Optional[int] = None
    em: Optional[int] = None
    loc: Optional[str] = None
    
    # Original fields for reference
    event_type: str # VISIT, MEETING, TODO, TIMETABLE
    status: str
    reference_id: int
    description: Optional[str] = None

class TimetableResponse(BaseModel):
    events: List[TimelineEvent]

import datetime as dt

class TimetableEventBase(BaseModel):
    title: str
    assignee_name: Optional[str] = None
    date: dt.date
    start_time: time
    end_time: time
    location: Optional[str] = None

class TimetableEventCreate(TimetableEventBase):
    pass

class TimetableEventUpdate(BaseModel):
    title: Optional[str] = None
    assignee_name: Optional[str] = None
    date: Optional[dt.date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    location: Optional[str] = None

class TimetableEventRead(TimetableEventBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
