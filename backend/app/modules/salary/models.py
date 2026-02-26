import enum
from datetime import datetime, UTC

from sqlalchemy import Column, Integer, String, ForeignKey, Date, Enum, Text, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class LeaveStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class LeaveRecord(Base):
    __tablename__ = "leave_records"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False)

    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    employee = relationship("app.modules.employees.models.Employee", back_populates="leaves")
    approver = relationship("app.modules.users.models.User", foreign_keys=[approved_by])

class SalarySlip(Base):
    __tablename__ = "salary_slips"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    month = Column(String, nullable=False) # YYYY-MM
    generated_at = Column(Date, default=lambda: datetime.now(UTC).date())

    
    base_salary = Column(Float, nullable=False)
    paid_leaves = Column(Integer, default=0)
    unpaid_leaves = Column(Integer, default=0)
    deduction_amount = Column(Float, default=0.0)
    final_salary = Column(Float, nullable=False)
    
    file_url = Column(String, nullable=True)

    employee = relationship("app.modules.employees.models.Employee", backref="salary_slips")
