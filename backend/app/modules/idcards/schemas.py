from pydantic import BaseModel
from datetime import date
from typing import Optional

class IDCardData(BaseModel):
    employee_name: str
    employee_code: str
    role: str
    joining_date: date
    photo_url: Optional[str] = None
    qr_data: str
