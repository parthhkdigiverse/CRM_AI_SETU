from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class MeetingSummaryBase(BaseModel):
    title: str
    content: str
    date: Optional[datetime] = None
    project_id: int

class MeetingSummaryCreate(BaseModel):
    title: str
    content: str
    date: Optional[datetime] = None

from app.modules.meetings.models import MeetingStatus

from app.modules.meetings.models import MeetingStatus

class MeetingSummaryUpdateBase(BaseModel):
     title: Optional[str] = None
     content: Optional[str] = None
     date: Optional[datetime] = None
     status: Optional[MeetingStatus] = None

class MeetingSummaryUpdate(MeetingSummaryUpdateBase):
    pass

class MeetingCancel(BaseModel):
    reason: Optional[str] = None

class MeetingSummaryRead(MeetingSummaryBase):
    id: int
    status: MeetingStatus
    cancellation_reason: Optional[str] = None

    class Config:
        from_attributes = True
