from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.modules.users.models import UserRole

class IncentiveTarget(Base):
    __tablename__ = "incentive_targets"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(Enum(UserRole), nullable=False)
    period = Column(String, nullable=False) # Monthly/Quarterly
    target_count = Column(Integer, nullable=False)

class IncentiveSlab(Base):
    __tablename__ = "incentive_slabs"

    id = Column(Integer, primary_key=True, index=True)
    min_percentage = Column(Float, nullable=False)
    amount_per_unit = Column(Float, nullable=False)

class EmployeePerformance(Base):
    __tablename__ = "employee_performances"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    period = Column(String, nullable=False) # YYYY-MM
    closed_units = Column(Integer, default=0)

    employee = relationship("app.modules.employees.models.Employee", backref="performances")

class IncentiveSlip(Base):
    __tablename__ = "incentive_slips"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    period = Column(String, nullable=False) # YYYY-MM
    
    target = Column(Integer, nullable=False)
    achieved = Column(Integer, nullable=False)
    percentage = Column(Float, nullable=False)
    applied_slab = Column(Float, nullable=True)
    amount_per_unit = Column(Float, default=0.0)
    total_incentive = Column(Float, nullable=False)
    
    generated_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("app.modules.employees.models.Employee", backref="incentive_slips")
