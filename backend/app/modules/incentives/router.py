from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from datetime import datetime, UTC

from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
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
    return db.query(IncentiveSlab).order_by(IncentiveSlab.min_units).all()

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

@router.get("/slips/{user_id}", response_model=List[IncentiveSlipRead])
def read_incentive_slips(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(pro_checker)
) -> Any:
    from app.modules.incentives.service import IncentiveService
    service = IncentiveService(db)
    return service.get_user_incentive_slips(user_id)

@router.delete("/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incentive_target(
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    db_target = db.query(IncentiveTarget).filter(IncentiveTarget.id == target_id).first()
    if not db_target:
        raise HTTPException(status_code=404, detail="Target not found")
    db.delete(db_target)
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

@router.delete("/slabs/{slab_id}")
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
    return {"message": "Slab deleted"}
