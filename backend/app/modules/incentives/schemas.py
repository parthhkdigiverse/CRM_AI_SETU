from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.modules.users.models import UserRole

# Targets
class IncentiveTargetBase(BaseModel):
    role: UserRole
    period: str # Monthly/Quarterly
    target_count: int

class IncentiveTargetCreate(IncentiveTargetBase):
    pass

class IncentiveTargetRead(IncentiveTargetBase):
    id: int
    class Config:
        from_attributes = True

# Slabs
class IncentiveSlabBase(BaseModel):
    min_percentage: float
    amount_per_unit: float

class IncentiveSlabCreate(IncentiveSlabBase):
    pass

class IncentiveSlabRead(IncentiveSlabBase):
    id: int
    class Config:
        from_attributes = True

# Calculation & Slips
class IncentiveCalculationRequest(BaseModel):
    employee_id: int
    period: str # YYYY-MM
    closed_units: int

class IncentiveSlipRead(BaseModel):
    id: int
    employee_id: int
    period: str
    target: int
    achieved: int
    percentage: float
    applied_slab: Optional[float]
    amount_per_unit: Optional[float]
    total_incentive: float
    generated_at: datetime

    class Config:
        from_attributes = True
