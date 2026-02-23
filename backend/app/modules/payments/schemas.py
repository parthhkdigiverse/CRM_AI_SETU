from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from app.modules.payments.models import PaymentStatus

class PaymentCreate(BaseModel):
    amount: float

class PaymentRead(BaseModel):
    id: int
    client_id: int
    amount: float
    qr_code_data: Optional[str] = None
    status: PaymentStatus
    generated_by_id: int
    verified_by_id: Optional[int] = None
    created_at: datetime
    verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InvoiceSendResponse(BaseModel):
    success: bool
    message: str
