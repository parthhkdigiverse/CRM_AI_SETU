# backend/app/modules/visits/schemas.py
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
    shop_name: Optional[str] = None
    area_name: Optional[str] = None
    user_name: Optional[str] = None
    photo_url: Optional[str] = None
    project_manager_name: Optional[str] = None
    shop_status: Optional[str] = None
    shop_demo_stage: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

