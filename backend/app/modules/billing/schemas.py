# backend/app/modules/billing/schemas.py
from typing import Optional
from pydantic import BaseModel, field_validator
from datetime import datetime


class BillCreate(BaseModel):
    # Client details (name + phone required)
    invoice_client_name: str
    invoice_client_phone: str
    invoice_client_email: Optional[str] = None
    invoice_client_address: Optional[str] = None
    invoice_client_org: Optional[str] = None

    # Optional shop/lead linkage
    shop_id: Optional[int] = None

    # Financial
    amount: float = 12000.0
    service_description: Optional[str] = "CRM AI SETU Software – Annual Subscription"

    @field_validator('invoice_client_name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Client name is required')
        return v.strip()

    @field_validator('invoice_client_phone')
    @classmethod
    def phone_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Client phone is required')
        return v.strip()


class BillRead(BaseModel):
    id: int
    shop_id: Optional[int] = None
    client_id: Optional[int] = None

    invoice_client_name: Optional[str] = None
    invoice_client_phone: Optional[str] = None
    invoice_client_email: Optional[str] = None
    invoice_client_address: Optional[str] = None
    invoice_client_org: Optional[str] = None

    amount: float
    invoice_status: str
    status: str
    invoice_number: Optional[str] = None
    whatsapp_sent: bool

    service_description: Optional[str] = None

    shop_name: Optional[str] = None
    client_name: Optional[str] = None

    created_by_id: Optional[int] = None
    verified_by_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
