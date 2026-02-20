from typing import Optional, List
from pydantic import BaseModel
from datetime import date
from app.modules.salary.models import LeaveStatus

# Leave Schemas
class LeaveApplicationCreate(BaseModel):
    start_date: date
    end_date: date
    reason: Optional[str] = None

class LeaveApproval(BaseModel):
    status: LeaveStatus # APPROVED or REJECTED

class LeaveRecordRead(BaseModel):
    id: int
    employee_id: int
    start_date: date
    end_date: date
    reason: Optional[str] = None
    status: LeaveStatus
    approved_by: Optional[int] = None

    class Config:
        from_attributes = True

# Salary Schemas
class SalarySlipGenerate(BaseModel):
    employee_id: int
    month: str # YYYY-MM
    paid_leaves: int = 0
    unpaid_leaves: int = 0
    deduction_amount: float = 0.0

class SalarySlipRead(BaseModel):
    id: int
    employee_id: int
    month: str
    base_salary: float
    paid_leaves: int
    unpaid_leaves: int
    deduction_amount: float
    final_salary: float
    generated_at: date

    class Config:
        from_attributes = True
