from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.modules.meetings.models import MeetingStatus, MeetingType

class MeetingSummaryBase(BaseModel):
    title: str
    content: str
    date: Optional[datetime] = None
    client_id: int
    meeting_type: Optional[MeetingType] = MeetingType.IN_PERSON

class MeetingSummaryCreate(BaseModel):
    title: str
    content: str
    date: Optional[datetime] = None
    meeting_type: Optional[MeetingType] = MeetingType.IN_PERSON
    status: Optional[MeetingStatus] = MeetingStatus.SCHEDULED

class MeetingSummaryUpdateBase(BaseModel):
     title: Optional[str] = None
     content: Optional[str] = None
     date: Optional[datetime] = None
     status: Optional[MeetingStatus] = None
     meeting_type: Optional[MeetingType] = None
     meet_link: Optional[str] = None

class MeetingSummaryUpdate(MeetingSummaryUpdateBase):
    pass

class MeetingCancel(BaseModel):
    reason: Optional[str] = None

class MeetingReschedule(BaseModel):
    new_date: datetime

class MeetingSummaryRead(MeetingSummaryBase):
    id: int
    status: MeetingStatus
    meet_link: Optional[str] = None
    cancellation_reason: Optional[str] = None

    class Config:
        from_attributes = True
