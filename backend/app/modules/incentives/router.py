from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from datetime import datetime, timezone
import json
from app.core.dependencies import RoleChecker, get_current_active_user
from app.modules.users.models import User, UserRole
from app.modules.incentives.models import IncentiveSlab, IncentiveSlip
from app.modules.incentives.schemas import IncentiveSlabCreate, IncentiveSlabRead, IncentiveSlabUpdate, IncentiveCalculationRequest, IncentiveSlipRead, IncentivePreviewResponse, IncentiveBulkCalculationRequest, IncentiveBulkCalculationResponse

router = APIRouter()

admin_checker = RoleChecker([UserRole.ADMIN])
staff_checker = RoleChecker([UserRole.ADMIN, UserRole.SALES, UserRole.TELESALES, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])

DEFAULT_FEATURE_ACCESS = {"incentive_manage_roles": ["ADMIN"], "incentive_view_all_roles": ["ADMIN"]}

def _current_role_name(current_user: User) -> str:
    return current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)

async def _get_feature_roles(feature_key: str) -> set:
    from app.modules.salary.models import AppSetting
    fallback = set(DEFAULT_FEATURE_ACCESS.get(feature_key, ["ADMIN"]))
    policy_row = await AppSetting.find_one(AppSetting.key == "ui_access_policy")
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

async def _require_feature_access(current_user: User, feature_key: str, detail: str = "Access denied") -> None:
    role_name = _current_role_name(current_user).upper()
    if role_name not in await _get_feature_roles(feature_key):
        raise HTTPException(status_code=403, detail=detail)

@router.post("/slabs", response_model=IncentiveSlabRead)
async def create_incentive_slab(slab_in: IncentiveSlabCreate, current_user: User = Depends(staff_checker)) -> Any:
    await _require_feature_access(current_user, "incentive_manage_roles", "You do not have permission to manage incentive slabs")
    db_slab = IncentiveSlab(**slab_in.model_dump())
    await db_slab.insert()
    return db_slab

@router.get("/slabs", response_model=List[IncentiveSlabRead])
async def read_incentive_slabs(current_user: User = Depends(staff_checker)) -> Any:
    return await IncentiveSlab.find_all().sort(+IncentiveSlab.min_units).to_list()

@router.put("/slabs/{slab_id}", response_model=IncentiveSlabRead)
async def update_incentive_slab(slab_id: str, slab_in: IncentiveSlabUpdate, current_user: User = Depends(staff_checker)) -> Any:
    await _require_feature_access(current_user, "incentive_manage_roles", "You do not have permission to manage incentive slabs")
    slab = await IncentiveSlab.find_one(IncentiveSlab.id == slab_id)
    if not slab:
        raise HTTPException(status_code=404, detail="Slab not found")
    update_data = slab_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(slab, field, value)
    await slab.save()
    return slab

@router.delete("/slabs/{slab_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incentive_slab(slab_id: str, current_user: User = Depends(staff_checker)):
    await _require_feature_access(current_user, "incentive_manage_roles", "You do not have permission to manage incentive slabs")
    db_slab = await IncentiveSlab.find_one(IncentiveSlab.id == slab_id)
    if not db_slab:
        raise HTTPException(status_code=404, detail="Slab not found")
    await db_slab.delete()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/slabs/batch-delete", status_code=status.HTTP_200_OK)
async def batch_delete_slabs(slab_ids: List[int], current_user: User = Depends(staff_checker)):
    await _require_feature_access(current_user, "incentive_manage_roles", "You do not have permission to manage incentive slabs")
    slabs = await IncentiveSlab.find(IncentiveSlab.id.in_(slab_ids)).to_list()
    for slab in slabs:
        await slab.delete()
    return {"message": f"Successfully deleted {len(slabs)} slabs"}

@router.post("/calculate/preview", response_model=IncentivePreviewResponse)
async def preview_incentive(calc_in: IncentiveCalculationRequest, current_user: User = Depends(staff_checker)) -> Any:
    await _require_feature_access(current_user, "incentive_manage_roles", "You do not have permission to calculate incentives")
    from app.modules.incentives.service import IncentiveService
    return await IncentiveService().preview_incentive(calc_in.user_id, calc_in.period, calc_in.closed_units)

@router.post("/calculate", response_model=IncentiveSlipRead)
async def calculate_incentive(calc_in: IncentiveCalculationRequest, current_user: User = Depends(staff_checker)) -> Any:
    await _require_feature_access(current_user, "incentive_manage_roles", "You do not have permission to calculate incentives")
    from app.modules.incentives.service import IncentiveService
    return await IncentiveService().calculate_incentive(calc_in)

@router.post("/calculate/bulk", response_model=IncentiveBulkCalculationResponse)
async def calculate_incentive_bulk(calc_in: IncentiveBulkCalculationRequest, current_user: User = Depends(staff_checker)) -> Any:
    await _require_feature_access(current_user, "incentive_manage_roles", "You do not have permission to calculate incentives")
    from app.modules.incentives.service import IncentiveService
    return await IncentiveService().calculate_incentive_bulk(calc_in.period)

@router.get("/slips", response_model=List[IncentiveSlipRead])
async def read_all_incentive_slips(current_user: User = Depends(staff_checker)) -> Any:
    await _require_feature_access(current_user, "incentive_view_all_roles", "You do not have permission to view all incentive slips")
    from app.modules.incentives.service import IncentiveService
    return await IncentiveService().get_all_incentive_slips()

@router.get("/my-slips", response_model=List[IncentiveSlipRead])
async def read_my_incentive_slips(current_user: User = Depends(staff_checker)) -> Any:
    from app.modules.incentives.service import IncentiveService
    return await IncentiveService().get_visible_user_incentive_slips(current_user.id)

@router.get("/slips/{user_id}", response_model=List[IncentiveSlipRead])
async def read_incentive_slips(user_id: str, current_user: User = Depends(staff_checker)) -> Any:
    can_view_all = _current_role_name(current_user).upper() in await _get_feature_roles("incentive_view_all_roles")
    if not can_view_all and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    from app.modules.incentives.service import IncentiveService
    return await IncentiveService().get_user_incentive_slips(user_id)

@router.patch("/slips/{slip_id}/remarks", response_model=IncentiveSlipRead)
async def update_incentive_slip_remarks(slip_id: str, payload: dict, current_user: User = Depends(staff_checker)) -> Any:
    slip = await IncentiveSlip.find_one(IncentiveSlip.id == slip_id)
    if not slip:
        raise HTTPException(status_code=404, detail="Slip not found")
    can_manage = _current_role_name(current_user).upper() in await _get_feature_roles("incentive_manage_roles")
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
    await slip.save()
    user = await User.find_one(User.id == slip.user_id)
    res = IncentiveSlipRead.model_validate(slip.model_dump())
    res.user_name = user.name if user and user.name else (user.email if user else f"Employee #{slip.user_id}")
    return res

@router.patch("/slips/{slip_id}/visibility", response_model=IncentiveSlipRead)
async def update_incentive_slip_visibility(slip_id: str, payload: dict, current_user: User = Depends(staff_checker)) -> Any:
    await _require_feature_access(current_user, "incentive_manage_roles", "You do not have permission to change incentive visibility")
    slip = await IncentiveSlip.find_one(IncentiveSlip.id == slip_id)
    if not slip:
        raise HTTPException(status_code=404, detail="Slip not found")
    slip.is_visible_to_employee = bool(payload.get("is_visible_to_employee", False))
    await slip.save()
    user = await User.find_one(User.id == slip.user_id)
    res = IncentiveSlipRead.model_validate(slip.model_dump())
    res.user_name = user.name if user and user.name else (user.email if user else f"Employee #{slip.user_id}")
    return res
