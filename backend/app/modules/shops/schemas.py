from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class ShopStatus(str, Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    MEETING_SET = "MEETING_SET"
    CONVERTED = "CONVERTED"

class ShopBase(BaseModel):
    name: str
    address: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    source: Optional[str] = "Other"
    project_type: Optional[str] = None
    requirements: Optional[str] = None
    area_id: Optional[int] = None
    status: Optional[ShopStatus] = ShopStatus.NEW
    owner_id: Optional[int] = None

class ShopCreate(ShopBase):
    pass

class ShopUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    source: Optional[str] = None
    project_type: Optional[str] = None
    requirements: Optional[str] = None
    area_id: Optional[int] = None
    status: Optional[ShopStatus] = None
    owner_id: Optional[int] = None

class ShopRead(ShopBase):
    id: int
    owner_name: Optional[str] = None
    area_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
