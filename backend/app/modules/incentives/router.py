# backend/app/modules/incentives/router.py
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from datetime import datetime, UTC

from app.core.database import get_db
from app.core.dependencies import RoleChecker, get_current_active_user
from app.modules.users.models import User, UserRole
from app.modules.incentives.models import (
    IncentiveSlab, IncentiveSlip, EmployeePerformance
)
from app.modules.incentives.schemas import (
    IncentiveSlabCreate, IncentiveSlabRead, IncentiveSlabUpdate,
    IncentiveCalculationRequest, IncentiveSlipRead
)

router = APIRouter()

# Role checkers
admin_checker = RoleChecker([UserRole.ADMIN])
pro_checker = RoleChecker([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])
staff_checker = RoleChecker([
    UserRole.ADMIN, UserRole.SALES, UserRole.TELESALES,
    UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES
])

# ─── SLABS ───────────────────────────────────────────────────────────────────

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
    current_user: User = Depends(staff_checker)
) -> Any:
    return db.query(IncentiveSlab).order_by(IncentiveSlab.min_units).all()


@router.put("/slabs/{slab_id}", response_model=IncentiveSlabRead)
def update_incentive_slab(
    slab_id: int,
    slab_in: IncentiveSlabUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    slab = db.query(IncentiveSlab).filter(IncentiveSlab.id == slab_id).first()
    if not slab:
        raise HTTPException(status_code=404, detail="Slab not found")
    update_data = slab_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(slab, field, value)
    db.commit()
    db.refresh(slab)
    return slab


@router.delete("/slabs/{slab_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incentive_slab(
    slab_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    db_slab = db.query(IncentiveSlab).filter(IncentiveSlab.id == slab_id).first()
    if not db_slab:
        raise HTTPException(status_code=404, detail="Slab not found")
    db.delete(db_slab)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/slabs/batch-delete", status_code=status.HTTP_200_OK)
def batch_delete_slabs(
    slab_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    try:
        count = db.query(IncentiveSlab).filter(IncentiveSlab.id.in_(slab_ids)).delete(synchronize_session=False)
        db.commit()
        return {"message": f"Successfully deleted {count} slabs"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ─── CALCULATION ─────────────────────────────────────────────────────────────

@router.post("/calculate", response_model=IncentiveSlipRead)
def calculate_incentive(
    calc_in: IncentiveCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    from app.modules.incentives.service import IncentiveService
    service = IncentiveService(db)
    return service.calculate_incentive(calc_in)


# ─── SLIPS ───────────────────────────────────────────────────────────────────

@router.get("/slips", response_model=List[IncentiveSlipRead])
def read_all_incentive_slips(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """All incentive slips across all employees (any authenticated staff can view)."""
    from app.modules.incentives.service import IncentiveService
    service = IncentiveService(db)
    return service.get_all_incentive_slips()


@router.get("/my-slips", response_model=List[IncentiveSlipRead])
def read_my_incentive_slips(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """Current user's own incentive slips."""
    from app.modules.incentives.service import IncentiveService
    service = IncentiveService(db)
    return service.get_user_incentive_slips(current_user.id)


@router.get("/slips/{user_id}", response_model=List[IncentiveSlipRead])
def read_incentive_slips(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """Slips for a specific user. Any staff can view any employee's slips."""
    from app.modules.incentives.service import IncentiveService
    service = IncentiveService(db)
    return service.get_user_incentive_slips(user_id)

