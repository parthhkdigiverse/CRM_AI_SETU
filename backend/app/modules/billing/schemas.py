from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class BillBase(BaseModel):
    shop_id: int
    amount: float

class BillCreate(BillBase):
    pass

class BillRead(BillBase):
    id: int
    client_id: Optional[int] = None
    status: str
    invoice_number: Optional[str] = None
    whatsapp_sent: bool
    created_at: datetime

    class Config:
        from_attributes = True
