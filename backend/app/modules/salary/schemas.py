# backend/app/modules/salary/schemas.py
from typing import Optional, List, Any
from pydantic import BaseModel, field_validator
from datetime import date
from app.modules.salary.models import LeaveStatus, LeaveType, DayType, SalaryStatus

# Leave Schemas
class LeaveApplicationCreate(BaseModel):
    start_date: date
    end_date: date
    leave_type: str = "CASUAL"
    day_type: str = "FULL"  # FULL or HALF
    reason: str  # required

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Leave reason is required")
        return v.strip()

    @field_validator("leave_type")
    @classmethod
    def validate_leave_type(cls, v: str) -> str:
        valid = [lt.value for lt in LeaveType]
        if v not in valid:
            raise ValueError(f"leave_type must be one of {valid}")
        return v

    @field_validator("day_type")
    @classmethod
    def validate_day_type(cls, v: str) -> str:
        valid = [dt.value for dt in DayType]
        if v not in valid:
            raise ValueError(f"day_type must be one of {valid}")
        return v


class LeaveApproval(BaseModel):
    status: LeaveStatus  # APPROVED or REJECTED
    remarks: Optional[str] = None  # Admin remarks (reason for rejection etc.)


class LeaveRecordRead(BaseModel):
    id: int
    user_id: int
    start_date: date
    end_date: date
    leave_type: str = "CASUAL"
    day_type: str = "FULL"
    reason: Optional[str] = None
    status: LeaveStatus
    remarks: Optional[str] = None
    user_name: Optional[str] = None
    approver_name: Optional[str] = None
    approved_by: Optional[int] = None

    class Config:
        from_attributes = True


# Salary Schemas
class SalarySlipGenerate(BaseModel):
    user_id: int
    month: str  # YYYY-MM
    extra_deduction: float = 0.0  # Admin-applied manual deduction
    base_salary: Optional[float] = None  # Override employee profile base salary for this slip


class SalaryPreviewResponse(BaseModel):
    user_id: int
    user_name: str
    month: str
    base_salary: float
    working_days: int
    total_leave_days: int
    paid_leaves: int
    unpaid_leaves: int
    leave_deduction: float
    incentive_amount: float
    slab_bonus: float
    extra_deduction: float
    total_earnings: float
    final_salary: float
    approved_leaves: List[Any]
    has_existing_slip: bool = False


class SalarySlipRead(BaseModel):
    id: int
    user_id: int
    month: str
    base_salary: float
    paid_leaves: int
    unpaid_leaves: int
    deduction_amount: float
    incentive_amount: float
    slab_bonus: float = 0.0
    total_earnings: float
    final_salary: float
    status: str = "CONFIRMED"
    confirmed_by: Optional[int] = None
    user_name: Optional[str] = None
    confirmer_name: Optional[str] = None
    generated_at: date

    class Config:
        from_attributes = True

