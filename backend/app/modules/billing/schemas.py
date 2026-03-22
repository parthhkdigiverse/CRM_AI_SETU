# backend/app/modules/billing/schemas.py
from typing import Optional, Literal
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
    amount: Optional[float] = None
    payment_type: Literal["BUSINESS_ACCOUNT", "PERSONAL_ACCOUNT", "CASH"]
    gst_type: Literal["WITH_GST", "WITHOUT_GST"]
    service_description: Optional[str] = "Harikrushn DigiVerse LLP Software – Annual Subscription"

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
    payment_type: str
    gst_type: str
    invoice_series: str
    invoice_sequence: int
    requires_qr: bool
    invoice_status: str
    status: str
    invoice_number: Optional[str] = None
    whatsapp_sent: bool
    is_archived: bool = False

    service_description: Optional[str] = None

    shop_name: Optional[str] = None
    client_name: Optional[str] = None
    creator_name: Optional[str] = None

    created_by_id: Optional[int] = None
    verified_by_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BillingWorkflowResolveRequest(BaseModel):
    payment_type: Literal["BUSINESS_ACCOUNT", "PERSONAL_ACCOUNT", "CASH"]
    gst_type: Literal["WITH_GST", "WITHOUT_GST"]
    amount: Optional[float] = None


class BillingWorkflowResolveResponse(BaseModel):
    payment_type: str
    gst_type: str
    requires_qr: bool
    amount: float
    base_amount: float
    gst_amount: float
    total_amount: float
    amount_source: str
    qr_available: bool
    qr_image_url: Optional[str] = None
    payment_upi_id: Optional[str] = None
    payment_account_name: Optional[str] = None


class BillingInvoiceActionResponse(BaseModel):
    can_verify: bool
    can_send_whatsapp: bool
    can_archive: bool = False
    can_unarchive: bool = False
    can_delete_archived: bool = False
    allowed_verifier_roles: list[str]
