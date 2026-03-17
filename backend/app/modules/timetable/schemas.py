# backend/app/modules/timetable/schemas.py
from typing import Optional, List, Union
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date, time

class TimelineEvent(BaseModel):
    id: Union[int, str]
    title: str
    date: Optional[str] = None # YYYY-MM-DD or full ISO
    user: Optional[str] = None # Assignee/User name
    sh: Optional[int] = None
    sm: Optional[int] = None
    eh: Optional[int] = None
    em: Optional[int] = None
    loc: Optional[str] = None
    
    # Original fields for reference
    event_type: str # VISIT, MEETING, TODO, TIMETABLE, DEMO
    status: Optional[str] = None
    reference_id: Optional[int] = None
    description: Optional[str] = None
    meet_url: Optional[str] = None

    # New fields for generic calendar events
    start: Optional[str] = None
    end: Optional[str] = None
    backgroundColor: Optional[str] = None
    borderColor: Optional[str] = None
    textColor: Optional[str] = None
    allDay: Optional[bool] = None

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
