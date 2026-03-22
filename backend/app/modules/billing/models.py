from beanie import Document
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import field_validator

class Bill(Document):
    shop_id: Optional[str] = None
    client_id: Optional[str] = None
    invoice_client_name: Optional[str] = None
    invoice_client_phone: Optional[str] = None
    invoice_client_email: Optional[str] = None
    invoice_client_address: Optional[str] = None
    invoice_client_org: Optional[str] = None
    amount: float = 12000.0
    payment_type: str = "PERSONAL_ACCOUNT"
    gst_type: str = "WITH_GST"
    invoice_series: str = "INV"
    invoice_sequence: int = 1
    requires_qr: bool = True
    is_deleted: bool = False
    invoice_status: str = "DRAFT"
    status: str = "PENDING"
    invoice_number: Optional[str] = None
    whatsapp_sent: bool = False
    is_archived: bool = False
    created_by_id: Optional[str] = None
    verified_by_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    service_description: Optional[str] = "Harikrushn DigiVerse LLP Software – Annual Subscription"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("created_at", "updated_at", "verified_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> Any:
        if isinstance(v, str):
            for fmt in ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
        return v

    class Settings:
        name = "bills"

