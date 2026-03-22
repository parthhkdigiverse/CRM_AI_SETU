from beanie import PydanticObjectId
# backend/app/modules/clients/schemas.py
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
import re

# Client Schemas
class ClientBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    organization: Optional[str] = None
    address: Optional[str] = None
    project_type: Optional[str] = None
    requirements: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        digits_only = re.sub(r"\D", "", v)
        if len(digits_only) < 10:
            raise ValueError("Phone number must contain at least 10 digits")
        if not re.match(r"^[\d\+\-\s\(\)]+$", v):
            raise ValueError("Phone number contains invalid characters")
        return v

class ClientCreate(ClientBase):
    referral_code: Optional[str] = None
    owner_id: Optional[str] = None

class ClientUpdate(ClientBase):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    organization: Optional[str] = None
    address: Optional[str] = None
    project_type: Optional[str] = None
    requirements: Optional[str] = None
    owner_id: Optional[str] = None


class ClientPMAssign(BaseModel):
    pm_id: str

class ClientRead(BaseModel):
    id: Optional[PydanticObjectId] = None
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    organization: Optional[str] = None
    pm_id: Optional[str] = None
    pm_name: Optional[str] = None
    owner_id: Optional[str] = None
    address: Optional[str] = None
    project_type: Optional[str] = None
    requirements: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class PMWorkloadRead(BaseModel):
    pm_id: str
    pm_name: str
    pm_email: str
    role: str
    active_client_count: int

    class Config:
        from_attributes = True
        populate_by_name = True


class ClientPMHistoryRead(BaseModel):
    id: Optional[PydanticObjectId] = None
    client_id: str
    pm_id: str
    assigned_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True
