from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.modules.visits.models import VisitStatus

class VisitBase(BaseModel):
    lead_id: int
    visit_date: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[VisitStatus] = VisitStatus.SCHEDULED

class VisitCreate(VisitBase):
    pass

class VisitUpdate(BaseModel):
    status: Optional[VisitStatus] = None
    notes: Optional[str] = None
    visit_date: Optional[datetime] = None

class VisitRead(VisitBase):
    id: int
    user_id: int
    photo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
