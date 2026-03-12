from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class IncentiveSlab(Base):
    __tablename__ = "incentive_slabs"

    id = Column(Integer, primary_key=True, index=True)
    min_units = Column(Integer, nullable=False, default=1)
    max_units = Column(Integer, nullable=False, default=10)
    incentive_per_unit = Column(Float, nullable=False, default=0.0)
    slab_bonus = Column(Float, nullable=False, default=0.0)

class EmployeePerformance(Base):
    __tablename__ = "employee_performances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    period = Column(String, nullable=False)  # YYYY-MM
    closed_units = Column(Integer, default=0)

    user = relationship("User", backref="performances")

class IncentiveSlip(Base):
    __tablename__ = "incentive_slips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    period = Column(String, nullable=False)  # YYYY-MM

    target = Column(Integer, nullable=False)
    achieved = Column(Integer, nullable=False)
    percentage = Column(Float, nullable=False)
    applied_slab = Column(String, nullable=True)
    amount_per_unit = Column(Float, default=0.0)
    total_incentive = Column(Float, nullable=False)

    slab_bonus_amount = Column(Float, default=0.0)
    generated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="incentive_slips")

from app.modules.users.models import User

