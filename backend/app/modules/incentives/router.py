from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, UTC

from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.employees.models import Employee
from app.modules.incentives.models import (
    IncentiveTarget, IncentiveSlab, IncentiveSlip, EmployeePerformance
)
from app.modules.incentives.schemas import (
    IncentiveTargetCreate, IncentiveTargetRead,
    IncentiveSlabCreate, IncentiveSlabRead,
    IncentiveCalculationRequest, IncentiveSlipRead
)

router = APIRouter()

# Role checkers
admin_checker = RoleChecker([UserRole.ADMIN])
pro_checker = RoleChecker([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])

# TARGETS
@router.post("/targets", response_model=IncentiveTargetRead)
def create_incentive_target(
    target_in: IncentiveTargetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    db_target = IncentiveTarget(**target_in.model_dump())
    db.add(db_target)
    db.commit()
    db.refresh(db_target)
    return db_target

@router.get("/targets", response_model=List[IncentiveTargetRead])
def read_incentive_targets(
    db: Session = Depends(get_db),
    current_user: User = Depends(pro_checker)
) -> Any:
    return db.query(IncentiveTarget).all()

# SLABS
@router.post("/slabs", response_model=IncentiveSlabRead)
def create_incentive_slab(
    slab_in: IncentiveSlabCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    db_slab = IncentiveSlab(**slab_in.model_dump())
    db.add(db_slab)
    db.commit()
    db.refresh(db_slab)
    return db_slab

@router.get("/slabs", response_model=List[IncentiveSlabRead])
def read_incentive_slabs(
    db: Session = Depends(get_db),
    current_user: User = Depends(pro_checker)
) -> Any:
    return db.query(IncentiveSlab).order_by(IncentiveSlab.min_percentage).all()

# CALCULATION
@router.post("/calculate", response_model=IncentiveSlipRead)
def calculate_incentive(
    calc_in: IncentiveCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    from app.modules.incentives.service import IncentiveService
    service = IncentiveService(db)
    return service.calculate_incentive(calc_in)

@router.get("/slips/{employee_id}", response_model=List[IncentiveSlipRead])
def read_incentive_slips(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(pro_checker)
) -> Any:
    from app.modules.incentives.service import IncentiveService
    service = IncentiveService(db)
    return service.get_employee_incentive_slips(employee_id)
