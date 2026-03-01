from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
import re

# Client Schemas
class ClientBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
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
    owner_id: Optional[int] = None

class ClientUpdate(ClientBase):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    owner_id: Optional[int] = None


class ClientPMAssign(BaseModel):
    pm_id: int

class ClientRead(ClientBase):
    id: int
    pm_id: Optional[int] = None
    owner_id: Optional[int] = None
    address: Optional[str] = None
    project_type: Optional[str] = None
    requirements: Optional[str] = None

    class Config:
        from_attributes = True
