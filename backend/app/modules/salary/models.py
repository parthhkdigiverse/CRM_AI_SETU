import enum
from datetime import datetime, UTC

from sqlalchemy import Column, Integer, String, ForeignKey, Date, Enum, Text, Float, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


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


class LeaveRecord(Base):
    __tablename__ = "leave_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    leave_type = Column(String, nullable=False, server_default="CASUAL")
    day_type = Column(String, nullable=False, server_default="FULL")  # FULL or HALF
    reason = Column(Text, nullable=True)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    remarks = Column(Text, nullable=True)  # Admin remarks on rejection/approval
    is_deleted = Column(Boolean, default=False, index=True)

    user = relationship("User", foreign_keys=[user_id], backref="leave_records")
    approver = relationship("User", foreign_keys=[approved_by])


class SalarySlip(Base):
    __tablename__ = "salary_slips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    month = Column(String, nullable=False)  # YYYY-MM
    generated_at = Column(Date, default=lambda: datetime.now(UTC).date())

    base_salary = Column(Float, nullable=False)
    paid_leaves = Column(Integer, default=0)
    unpaid_leaves = Column(Integer, default=0)
    deduction_amount = Column(Float, default=0.0)
    incentive_amount = Column(Float, default=0.0)
    slab_bonus = Column(Float, default=0.0)
    total_earnings = Column(Float, nullable=False, default=0.0)
    final_salary = Column(Float, nullable=False)

    # Workflow: DRAFT → CONFIRMED
    status = Column(String, nullable=False, server_default="CONFIRMED")
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(Date, nullable=True)
    is_visible_to_employee = Column(Boolean, nullable=False, default=False, server_default="false")
    employee_remarks = Column(Text, nullable=True)
    manager_remarks = Column(Text, nullable=True)

    file_url = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False, index=True)

    user = relationship("User", foreign_keys=[user_id], backref="salary_slips")
    confirmer = relationship("User", foreign_keys=[confirmed_by])


class AppSetting(Base):
    """Application-wide key-value settings store."""
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(Text, nullable=True)


# Import models at the end to ensure they are registered without circular dependency issues
from app.modules.users.models import User


