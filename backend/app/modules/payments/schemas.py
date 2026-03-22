from beanie import PydanticObjectId
# backend/app/modules/payments/schemas.py
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from app.modules.payments.models import PaymentStatus

class PaymentCreate(BaseModel):
    amount: float

class PaymentRead(BaseModel):
    id: Optional[PydanticObjectId] = None
    client_id: str
    amount: float
    qr_code_data: Optional[str] = None
    status: PaymentStatus
    generated_by_id: str
    verified_by_id: Optional[str] = None
    created_at: datetime
    verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class InvoiceSendResponse(BaseModel):
    success: bool
    message: str
