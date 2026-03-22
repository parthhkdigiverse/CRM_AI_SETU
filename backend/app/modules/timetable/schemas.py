from typing import Optional, List, Union
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date, time
import datetime as dt
from beanie import PydanticObjectId

class TimelineEvent(BaseModel):
    id: Union[PydanticObjectId, str] = Field(alias="_id")
    title: str
    date: Optional[str] = None 
    user: Optional[str] = None 
    sh: Optional[int] = None
    sm: Optional[int] = None
    eh: Optional[int] = None
    em: Optional[int] = None
    loc: Optional[str] = None
    
    event_type: str 
    status: Optional[str] = None
    reference_id: Optional[str] = None # String karyu MongoDB mate
    description: Optional[str] = None
    meet_url: Optional[str] = None

    start: Optional[str] = None
    end: Optional[str] = None
    backgroundColor: Optional[str] = None
    borderColor: Optional[str] = None
    textColor: Optional[str] = None
    allDay: Optional[bool] = None

    model_config = ConfigDict(populate_by_name=True)

class TimetableResponse(BaseModel):
    events: List[TimelineEvent]

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
    id: PydanticObjectId = Field(alias="_id")
    user_id: str # String karyu MongoDB mate

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )