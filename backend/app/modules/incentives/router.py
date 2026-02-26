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
    from sqlalchemy import extract
    from app.modules.clients.models import Client
    
    employee = db.query(Employee).filter(Employee.id == calc_in.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    existing_slip = db.query(IncentiveSlip).filter(
        IncentiveSlip.employee_id == calc_in.employee_id,
        IncentiveSlip.period == calc_in.period
    ).first()
    if existing_slip:
        raise HTTPException(status_code=400, detail="Incentive slip for this period already exists")

    user = db.query(User).filter(User.id == employee.user_id).first()
    
    # Determined Target
    target = employee.target
    if target == 0 and user:
        # Fallback to Role based target
        role_target = db.query(IncentiveTarget).filter(
            IncentiveTarget.role == user.role,
            IncentiveTarget.period == "Monthly" # Assumption
        ).first()
        if role_target:
            target = role_target.target_count
            
    if target == 0:
        raise HTTPException(status_code=400, detail="Target not set for employee or role")

    if calc_in.closed_units is not None:
        achieved = calc_in.closed_units
    else:
        year, month = map(int, calc_in.period.split('-'))
        achieved = 0
        if user.role in [UserRole.SALES, UserRole.TELESALES, UserRole.PROJECT_MANAGER_AND_SALES]:
            achieved += db.query(Client).filter(
                Client.owner_id == user.id,
                extract('year', Client.created_at) == year,
                extract('month', Client.created_at) == month
            ).count()
        if user.role in [UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]:
            achieved += db.query(Client).filter(
                Client.pm_id == user.id,
                extract('year', Client.created_at) == year,
                extract('month', Client.created_at) == month
            ).count()
            
    percentage = (achieved / target) * 100
    
    # Find Slab
    # Order by min_percentage desc to find highest match
    applied_slab = db.query(IncentiveSlab).filter(
        IncentiveSlab.min_percentage <= percentage
    ).order_by(IncentiveSlab.min_percentage.desc()).first()
    
    amount_per_unit = 0.0
    total_incentive = 0.0
    applied_slab_val = 0.0
    
    if applied_slab:
        amount_per_unit = applied_slab.amount_per_unit
        total_incentive = achieved * amount_per_unit
        applied_slab_val = applied_slab.min_percentage
        
    # Create Slip
    db_slip = IncentiveSlip(
        employee_id=calc_in.employee_id,
        period=calc_in.period,
        target=target,
        achieved=achieved,
        percentage=round(percentage, 2),
        applied_slab=applied_slab_val,
        amount_per_unit=amount_per_unit,
        total_incentive=round(total_incentive, 2),
        generated_at=datetime.now(UTC)

    )
    db.add(db_slip)
    db.commit()
    db.refresh(db_slip)
    
    return db_slip

@router.get("/slips/{employee_id}", response_model=List[IncentiveSlipRead])
def read_incentive_slips(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(pro_checker)
) -> Any:
    return db.query(IncentiveSlip).filter(IncentiveSlip.employee_id == employee_id).all()
