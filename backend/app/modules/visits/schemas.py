from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.modules.visits.models import VisitStatus

class VisitBase(BaseModel):
    shop_id: int
    status: Optional[VisitStatus] = VisitStatus.SATISFIED
    remarks: Optional[str] = None
    decline_remarks: Optional[str] = None
    visit_date: Optional[datetime] = None

class VisitCreate(VisitBase):
    pass

class VisitUpdate(BaseModel):
    status: Optional[VisitStatus] = None
    remarks: Optional[str] = None
    decline_remarks: Optional[str] = None
    visit_date: Optional[datetime] = None

class VisitRead(VisitBase):

    id: int
    user_id: int
    photo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
