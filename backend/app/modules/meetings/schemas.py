from beanie import PydanticObjectId
# backend/app/modules/meetings/schemas.py
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.enums import GlobalTaskStatus
from app.modules.meetings.models import MeetingType


class MeetingSummaryBase(BaseModel):
    title: str
    content: str
    date: Optional[datetime] = None
    client_id: str
    meeting_type: Optional[MeetingType] = MeetingType.IN_PERSON


class MeetingSummaryCreate(BaseModel):
    title: str
    content: str
    date: Optional[datetime] = None
    meeting_type: Optional[MeetingType] = MeetingType.IN_PERSON
    status: Optional[GlobalTaskStatus] = GlobalTaskStatus.OPEN


class MeetingSummaryUpdateBase(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    date: Optional[datetime] = None
    status: Optional[GlobalTaskStatus] = None
    meeting_type: Optional[MeetingType] = None
    meet_link: Optional[str] = None


class MeetingSummaryUpdate(MeetingSummaryUpdateBase):
    pass


class MeetingCancel(BaseModel):
    reason: Optional[str] = None


class MeetingReschedule(BaseModel):
    new_date: datetime


class MeetingSummaryRead(MeetingSummaryBase):
    id: Optional[PydanticObjectId] = None
    status: GlobalTaskStatus
    meet_link: Optional[str] = None
    cancellation_reason: Optional[str] = None
    todo_id: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True
