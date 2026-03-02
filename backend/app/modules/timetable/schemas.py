from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class TimelineEvent(BaseModel):
    id: int
    title: str
    date: datetime
    event_type: str # VISIT, MEETING, TODO
    status: str
    reference_id: int
    description: Optional[str] = None

class TimetableResponse(BaseModel):
    events: List[TimelineEvent]
