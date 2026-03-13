# backend/app/modules/incentives/schemas.py
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

# Slabs
class IncentiveSlabBase(BaseModel):
    min_units: int
    max_units: int
    incentive_per_unit: float
    slab_bonus: float

class IncentiveSlabCreate(IncentiveSlabBase):
    pass

class IncentiveSlabUpdate(BaseModel):
    min_units: Optional[int] = None
    max_units: Optional[int] = None
    incentive_per_unit: Optional[float] = None
    slab_bonus: Optional[float] = None

class IncentiveSlabRead(IncentiveSlabBase):
    id: int
    class Config:
        from_attributes = True

# Calculation & Slips
class IncentiveCalculationRequest(BaseModel):
    user_id: int
    period: str  # YYYY-MM
    closed_units: Optional[int] = None
    force_recalculate: bool = False


class IncentiveBulkCalculationRequest(BaseModel):
    period: str  # YYYY-MM


class IncentiveBulkCalculationResponse(BaseModel):
    period: str
    processed_users: int
    created_slips: int
    skipped_existing: int
    skipped_disabled: int
    failed_users: int
    failures: list[dict]

class IncentiveSlipRead(BaseModel):
    id: int
    user_id: int
    period: str
    target: int
    achieved: int
    percentage: float
    applied_slab: Optional[str]
    amount_per_unit: Optional[float]
    slab_bonus_amount: Optional[float] = 0.0
    total_incentive: float
    generated_at: datetime
    user_name: Optional[str] = None

    class Config:
        from_attributes = True


class IncentivePreviewResponse(BaseModel):
    user_id: int
    user_name: str
    period: str
    target: int
    confirmed_tasks: int
    pending_tasks: int
    refunded_tasks: int
    total_tasks_in_period: int
    slab_range: Optional[str]
    incentive_per_task: float
    base_incentive: float
    slab_bonus: float
    total_incentive: float
    percentage: float
    slip_exists: bool

