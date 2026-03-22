# backend/app/modules/salary/models.py
import enum
from datetime import datetime, UTC
from typing import Optional, Annotated, List
from beanie import Document, Indexed, Link
from pydantic import Field

class LeaveType(str, enum.Enum):
    ANNUAL = "ANNUAL"
    SICK = "SICK"
    CASUAL = "CASUAL"
    UNPAID = "UNPAID"
    OTHER = "OTHER"

class DayType(str, enum.Enum):
    FULL = "FULL"
    HALF = "HALF"

class LeaveStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class SalaryStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"

class LeaveRecord(Document):
    # MongoDB ma user_id string (ObjectId) hoy chhe
    user_id: str 
    start_date: datetime
    end_date: datetime
    leave_type: str = "CASUAL"
    day_type: str = "FULL"  # FULL or HALF
    reason: Optional[str] = None
    status: LeaveStatus = LeaveStatus.PENDING
    approved_by: Optional[str] = None
    remarks: Optional[str] = None
    is_deleted: bool = False

    class Settings:
        name = "leave_records" # Table name na badle Collection name

class SalarySlip(Document):
    user_id: str
    month: str  # YYYY-MM
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    base_salary: float
    paid_leaves: int = 0
    unpaid_leaves: int = 0
    deduction_amount: float = 0.0
    incentive_amount: float = 0.0
    slab_bonus: float = 0.0
    total_earnings: float = 0.0
    final_salary: float

    status: str = "CONFIRMED"
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    is_visible_to_employee: bool = False
    employee_remarks: Optional[str] = None
    manager_remarks: Optional[str] = None

    file_url: Optional[str] = None
    is_deleted: bool = False

    class Settings:
        name = "salary_slips"

class AppSetting(Document):
    key: Annotated[str, Indexed(unique=True)]
    value: Optional[str] = None

    class Settings:
        name = "app_settings"