from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.modules.leads.models import LeadStatus

class LeadBase(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    company_name: Optional[str] = None
    address: Optional[str] = None
    status: Optional[LeadStatus] = LeadStatus.NEW
    area_id: Optional[int] = None

class LeadCreate(LeadBase):
    pass

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    address: Optional[str] = None
    status: Optional[LeadStatus] = None
    area_id: Optional[int] = None

class LeadRead(LeadBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
