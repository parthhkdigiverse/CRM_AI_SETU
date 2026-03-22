from beanie import Document
from typing import Optional
from datetime import datetime, timezone
import enum

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"

class Payment(Document):
    client_id: str
    amount: float
    qr_code_data: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    generated_by_id: str
    verified_by_id: Optional[str] = None
    created_at: datetime = datetime.now(timezone.utc)
    is_deleted: bool = False
    verified_at: Optional[datetime] = None

    class Settings:
        name = "payments"
