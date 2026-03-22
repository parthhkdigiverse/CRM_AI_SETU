from beanie import Document
from typing import Optional
from datetime import datetime, timezone

class IncentiveSlab(Document):
    min_units: int = 1
    max_units: int = 10
    incentive_per_unit: float = 0.0
    slab_bonus: float = 0.0

    class Settings:
        name = "incentive_slabs"

class EmployeePerformance(Document):
    user_id: str
    period: str
    closed_units: int = 0

    class Settings:
        name = "employee_performances"

class IncentiveSlip(Document):
    user_id: str
    period: str
    target: int
    achieved: int
    percentage: float
    applied_slab: Optional[str] = None
    amount_per_unit: float = 0.0
    total_incentive: float
    slab_bonus_amount: float = 0.0
    is_visible_to_employee: bool = False
    employee_remarks: Optional[str] = None
    manager_remarks: Optional[str] = None
    generated_at: datetime = datetime.now(timezone.utc)

    class Settings:
        name = "incentive_slips"
