# backend/app/modules/incentives/router.py
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from datetime import datetime, UTC
import json

from app.core.database import get_db
from app.core.dependencies import RoleChecker, get_current_active_user
from app.modules.users.models import User, UserRole
from app.modules.incentives.models import (
    IncentiveSlab, IncentiveSlip, EmployeePerformance
)
from app.modules.incentives.schemas import (
    IncentiveSlabCreate, IncentiveSlabRead, IncentiveSlabUpdate,
    IncentiveCalculationRequest, IncentiveSlipRead, IncentivePreviewResponse,
    IncentiveBulkCalculationRequest, IncentiveBulkCalculationResponse
)
from app.modules.salary.models import AppSetting

router = APIRouter()

# Role checkers
admin_checker = RoleChecker([UserRole.ADMIN])
pro_checker = RoleChecker([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])
staff_checker = RoleChecker([
    UserRole.ADMIN, UserRole.SALES, UserRole.TELESALES,
    UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES
])


DEFAULT_FEATURE_ACCESS = {
    "incentive_manage_roles": ["ADMIN"],
    "incentive_view_all_roles": ["ADMIN"],
}


def _current_role_name(current_user: User) -> str:
    return current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)


def _get_feature_roles(db: Session, feature_key: str) -> set[str]:
    fallback = set(DEFAULT_FEATURE_ACCESS.get(feature_key, ["ADMIN"]))
    policy_row = db.query(AppSetting).filter(AppSetting.key == "ui_access_policy").first()
    if not policy_row or not policy_row.value:
        return fallback
    try:
        data = json.loads(policy_row.value)
        feature_access = data.get("feature_access") or {}
        configured = feature_access.get(feature_key)
        if isinstance(configured, list) and configured:
            return {str(r).upper() for r in configured if str(r).strip()}
    except Exception:
        return fallback
    return fallback


def _require_feature_access(db: Session, current_user: User, feature_key: str, detail: str = "Access denied") -> None:
    role_name = _current_role_name(current_user).upper()
    if role_name not in _get_feature_roles(db, feature_key):
        raise HTTPException(status_code=403, detail=detail)

# ─── SLABS ───────────────────────────────────────────────────────────────────

@router.post("/slabs", response_model=IncentiveSlabRead)
def create_incentive_slab(
    slab_in: IncentiveSlabCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "incentive_manage_roles", "You do not have permission to manage incentive slabs")

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
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "incentive_manage_roles", "You do not have permission to manage incentive slabs")

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
    current_user: User = Depends(staff_checker)
):
    _require_feature_access(db, current_user, "incentive_manage_roles", "You do not have permission to manage incentive slabs")

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
    current_user: User = Depends(staff_checker)
):
    _require_feature_access(db, current_user, "incentive_manage_roles", "You do not have permission to manage incentive slabs")

    try:
        count = db.query(IncentiveSlab).filter(IncentiveSlab.id.in_(slab_ids)).delete(synchronize_session=False)
        db.commit()
        return {"message": f"Successfully deleted {count} slabs"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ─── CALCULATION ─────────────────────────────────────────────────────────────

@router.post("/calculate/preview", response_model=IncentivePreviewResponse)
def preview_incentive(
    calc_in: IncentiveCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "incentive_manage_roles", "You do not have permission to calculate incentives")

    """Preview incentive calculation (10-day lock + refund logic). Does not save."""
    from app.modules.incentives.service import IncentiveService
    service = IncentiveService(db)
    return service.preview_incentive(calc_in.user_id, calc_in.period, calc_in.closed_units)


@router.post("/calculate", response_model=IncentiveSlipRead)
def calculate_incentive(
    calc_in: IncentiveCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "incentive_manage_roles", "You do not have permission to calculate incentives")

    from app.modules.incentives.service import IncentiveService
    service = IncentiveService(db)
    return service.calculate_incentive(calc_in)


@router.post("/calculate/bulk", response_model=IncentiveBulkCalculationResponse)
def calculate_incentive_bulk(
    calc_in: IncentiveBulkCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "incentive_manage_roles", "You do not have permission to calculate incentives")

    from app.modules.incentives.service import IncentiveService
    service = IncentiveService(db)
    return service.calculate_incentive_bulk(calc_in.period)


# ─── SLIPS ───────────────────────────────────────────────────────────────────

@router.get("/slips", response_model=List[IncentiveSlipRead])
def read_all_incentive_slips(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "incentive_view_all_roles", "You do not have permission to view all incentive slips")

    """All incentive slips across all employees (admin only)."""
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
    return service.get_visible_user_incentive_slips(current_user.id)


@router.get("/slips/{user_id}", response_model=List[IncentiveSlipRead])
def read_incentive_slips(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """Slips for a specific user. Non-admin users can access only their own slips."""
    can_view_all = _current_role_name(current_user).upper() in _get_feature_roles(db, "incentive_view_all_roles")
    if not can_view_all and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    from app.modules.incentives.service import IncentiveService
    service = IncentiveService(db)
    return service.get_user_incentive_slips(user_id)


@router.patch("/slips/{slip_id}/remarks", response_model=IncentiveSlipRead)
def update_incentive_slip_remarks(
    slip_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    slip = db.query(IncentiveSlip).filter(IncentiveSlip.id == slip_id).first()
    if not slip:
        raise HTTPException(status_code=404, detail="Slip not found")

    can_manage = _current_role_name(current_user).upper() in _get_feature_roles(db, "incentive_manage_roles")
    employee_remarks = payload.get("employee_remarks")
    manager_remarks = payload.get("manager_remarks")

    if can_manage:
        if employee_remarks is not None:
            slip.employee_remarks = str(employee_remarks).strip() or None
        if manager_remarks is not None:
            slip.manager_remarks = str(manager_remarks).strip() or None
    else:
        if slip.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You can update remarks only for your own incentive slip")
        if not getattr(slip, "is_visible_to_employee", False):
            raise HTTPException(status_code=400, detail="Remarks can be added only after slip is released")
        if employee_remarks is None:
            raise HTTPException(status_code=400, detail="employee_remarks is required")
        slip.employee_remarks = str(employee_remarks).strip() or None

    db.commit()
    db.refresh(slip)
    res = IncentiveSlipRead.model_validate(slip)
    res.user_name = slip.user.name if slip.user and slip.user.name else (slip.user.email if slip.user else f"Employee #{slip.user_id}")
    return res


@router.patch("/slips/{slip_id}/visibility", response_model=IncentiveSlipRead)
def update_incentive_slip_visibility(
    slip_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "incentive_manage_roles", "You do not have permission to change incentive visibility")

    slip = db.query(IncentiveSlip).filter(IncentiveSlip.id == slip_id).first()
    if not slip:
        raise HTTPException(status_code=404, detail="Slip not found")

    slip.is_visible_to_employee = bool(payload.get("is_visible_to_employee", False))
    db.commit()
    db.refresh(slip)
    res = IncentiveSlipRead.model_validate(slip)
    res.user_name = slip.user.name if slip.user and slip.user.name else (slip.user.email if slip.user else f"Employee #{slip.user_id}")
    return res

