from typing import Optional
from pydantic import BaseModel
from datetime import date

class EmployeeBase(BaseModel):
    employee_code: str
    joining_date: date
    base_salary: float = 0.0
    target: int = 0
    department: Optional[str] = None

class EmployeeCreate(EmployeeBase):
    user_id: int

class EmployeeUpdate(BaseModel):
    employee_code: Optional[str] = None
    joining_date: Optional[date] = None
    base_salary: Optional[float] = None
    target: Optional[int] = None
    department: Optional[str] = None

from app.modules.users.models import UserRole

class EmployeeRead(EmployeeBase):
    id: int
    user_id: int
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    referral_code: Optional[str] = None

    class Config:
        from_attributes = True

class ReferralCodeCreate(BaseModel):
    code: Optional[str] = None

class ReferralCodeRead(BaseModel):
    employee_id: int
    code: str

from app.modules.users.models import UserRole
class EmployeeRoleUpdate(BaseModel):
    role: UserRole
