from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from datetime import datetime, UTC
import json

# MongoDB (Beanie) ma get_db ni jarur nathi
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.salary.models import LeaveRecord, SalarySlip, LeaveStatus, AppSetting
from app.modules.salary.schemas import (
    LeaveApplicationCreate, LeaveRecordRead, LeaveApproval,
    SalarySlipGenerate, SalarySlipRead, SalaryPreviewResponse
)

router = APIRouter()

# Role checkers
hr_checker = RoleChecker([UserRole.ADMIN])
staff_checker = RoleChecker([
    UserRole.ADMIN,
    UserRole.SALES,
    UserRole.TELESALES,
    UserRole.PROJECT_MANAGER,
    UserRole.PROJECT_MANAGER_AND_SALES
])

DEFAULT_FEATURE_ACCESS = {
    "leave_apply_roles": ["SALES", "TELESALES", "PROJECT_MANAGER", "PROJECT_MANAGER_AND_SALES"],
    "leave_edit_own_roles": ["SALES", "TELESALES", "PROJECT_MANAGER", "PROJECT_MANAGER_AND_SALES"],
    "leave_cancel_own_roles": ["SALES", "TELESALES", "PROJECT_MANAGER", "PROJECT_MANAGER_AND_SALES"],
    "leave_manage_roles": ["ADMIN"],
    "salary_manage_roles": ["ADMIN"],
    "salary_view_all_roles": ["ADMIN"],
}

def _current_role_name(current_user: User) -> str:
    return current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)

async def _get_feature_roles(feature_key: str) -> set[str]:
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
    allowed = await _get_feature_roles(feature_key)
    if role_name not in allowed:
        raise HTTPException(status_code=403, detail=detail)

# ═══════════════════════════════════════════════════════
# LEAVE ENDPOINTS
# ═══════════════════════════════════════════════════════

@router.post("/leave", response_model=LeaveRecordRead)
async def apply_leave(
    leave_in: LeaveApplicationCreate,
    current_user: User = Depends(staff_checker)
) -> Any:
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin cannot apply leave")

    await _require_feature_access(current_user, "leave_apply_roles", "You do not have permission to apply leave")

    if leave_in.end_date < leave_in.start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    db_leave = LeaveRecord(
        user_id=str(current_user.id),
        start_date=leave_in.start_date,
        end_date=leave_in.end_date,
        leave_type=leave_in.leave_type,
        day_type=leave_in.day_type,
        reason=leave_in.reason,
        status=LeaveStatus.PENDING,
    )
    await db_leave.insert()
    return await _leave_to_dict(db_leave, current_user)

@router.patch("/leave/{leave_id}/approve", response_model=LeaveRecordRead)
async def approve_leave(
    leave_id: str,
    approval_in: LeaveApproval,
    current_user: User = Depends(staff_checker)
) -> Any:
    await _require_feature_access(current_user, "leave_manage_roles", "You do not have permission to approve/reject leave")

    db_leave = await LeaveRecord.find_one(LeaveRecord.id == leave_id, LeaveRecord.is_deleted == False)
    if not db_leave:
        raise HTTPException(status_code=404, detail="Leave record not found")

    db_leave.status = approval_in.status
    if approval_in.status == LeaveStatus.APPROVED:
        db_leave.approved_by = str(current_user.id)
    if approval_in.remarks is not None:
        db_leave.remarks = approval_in.remarks.strip() or None

    await db_leave.save()
    return await _leave_to_dict(db_leave)

@router.get("/leave", response_model=List[LeaveRecordRead])
async def get_my_leaves(
    current_user: User = Depends(staff_checker)
) -> Any:
    leaves = await LeaveRecord.find(
        LeaveRecord.user_id == str(current_user.id),
        LeaveRecord.is_deleted == False
    ).sort(-LeaveRecord.start_date).to_list()
    return [await _leave_to_dict(l) for l in leaves]

@router.get("/leave/all", response_model=List[LeaveRecordRead])
async def get_all_leaves(
    current_user: User = Depends(staff_checker)
) -> Any:
    await _require_feature_access(current_user, "leave_manage_roles", "You do not have permission to view all leave records")
    leaves = await LeaveRecord.find(LeaveRecord.is_deleted == False).sort(-LeaveRecord.start_date).to_list()
    return [await _leave_to_dict(l) for l in leaves]

@router.patch("/leave/{leave_id}", response_model=LeaveRecordRead)
async def update_my_leave(
    leave_id: str,
    leave_in: LeaveApplicationCreate,
    current_user: User = Depends(staff_checker)
) -> Any:
    await _require_feature_access(current_user, "leave_edit_own_roles", "You do not have permission to edit leave")

    db_leave = await LeaveRecord.find_one(LeaveRecord.id == leave_id, LeaveRecord.is_deleted == False)
    if not db_leave:
        raise HTTPException(status_code=404, detail="Leave record not found")
    if db_leave.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="You can edit only your own leave")
    if db_leave.status != LeaveStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending leave can be edited")
    
    db_leave.start_date = leave_in.start_date
    db_leave.end_date = leave_in.end_date
    db_leave.leave_type = leave_in.leave_type
    db_leave.day_type = leave_in.day_type
    db_leave.reason = leave_in.reason
    await db_leave.save()
    return await _leave_to_dict(db_leave, current_user)

@router.get("/leave/summary/{user_id}")
async def get_leave_summary(
    user_id: str,
    month: str = Query(..., description="YYYY-MM"),
    current_user: User = Depends(staff_checker)
) -> Any:
    if current_user.role != UserRole.ADMIN and user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    year, month_num = map(int, month.split('-'))
    # MongoDB summary logic
    leaves = await LeaveRecord.find(
        LeaveRecord.user_id == user_id,
        LeaveRecord.is_deleted == False
    ).to_list()
    
    # Filter by month/year in Python for simplicity with Beanie
    filtered_leaves = [l for l in leaves if l.start_date.year == year and l.start_date.month == month_num]

    total, approved, pending, rejected = 0, 0, 0, 0
    for l in filtered_leaves:
        days = (l.end_date - l.start_date).days + 1
        total += days
        if l.status == LeaveStatus.APPROVED: approved += days
        elif l.status == LeaveStatus.PENDING: pending += days
        else: rejected += days

    return {
        "user_id": user_id, "month": month, "total_leave_days": total,
        "approved_days": approved, "pending_days": pending, "rejected_days": rejected,
        "paid_leaves": min(approved, 1), "unpaid_leaves": max(0, approved - 1),
    }

@router.delete("/leave/{leave_id}", status_code=204, response_class=Response)
async def delete_leave(
    leave_id: str,
    current_user: User = Depends(staff_checker)
) -> Response:
    leave = await LeaveRecord.find_one(LeaveRecord.id == leave_id, LeaveRecord.is_deleted == False)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")

    role_name = _current_role_name(current_user).upper()
    can_manage = role_name in await _get_feature_roles("leave_manage_roles")
    
    if can_manage:
        policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
        if policy and policy.value == "HARD":
            await leave.delete()
        else:
            leave.is_deleted = True
            await leave.save()
        return Response(status_code=204)

    if leave.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="You can cancel only your own leave")
    
    leave.is_deleted = True
    await leave.save()
    return Response(status_code=204)

# ═══════════════════════════════════════════════════════
# SALARY ENDPOINTS
# ═══════════════════════════════════════════════════════

@router.get("/salary/preview")
async def preview_salary(
    user_id: str = Query(...),
    month: str = Query(...),
    extra_deduction: float = Query(0.0),
    base_salary: float = Query(None),
    current_user: User = Depends(staff_checker)
) -> Any:
    await _require_feature_access(current_user, "salary_manage_roles")
    from app.modules.salary.service import SalaryService
    # SalaryService should be async now
    return await SalaryService().preview_salary(user_id, month, extra_deduction, base_salary=base_salary)

@router.get("/salary/me")
async def get_my_salary_slips(
    current_user: User = Depends(staff_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    return await SalaryService().get_user_salary_slips(str(current_user.id), show_drafts=False, only_visible=True)

@router.get("/salary/slip/{slip_id}/invoice")
async def get_salary_invoice(
    slip_id: str,
    current_user: User = Depends(staff_checker)
) -> Any:
    from fastapi.responses import HTMLResponse
    from app.modules.salary.service import SalaryService
    
    slip = await SalarySlip.find_one(SalarySlip.id == slip_id, SalarySlip.is_deleted == False)
    if not slip:
        raise HTTPException(status_code=404, detail="Slip not found")
    
    html = await SalaryService().generate_invoice_html(slip_id)
    return HTMLResponse(content=html)

# ═══════════════════════════════════════════════════════
# PAYSLIP COMPANY SETTINGS
# ═══════════════════════════════════════════════════════

@router.get("/payslip-settings")
async def get_payslip_settings(current_user: User = Depends(staff_checker)) -> Any:
    email_row = await AppSetting.find_one(AppSetting.key == "payslip_email")
    phone_row = await AppSetting.find_one(AppSetting.key == "payslip_phone")
    return {
        "email": email_row.value if email_row else "hrmangukiya3494@gmail.com",
        "phone": phone_row.value if phone_row else "8866005029",
    }

@router.put("/payslip-settings")
async def update_payslip_settings(payload: dict, current_user: User = Depends(staff_checker)) -> Any:
    await _require_feature_access(current_user, "salary_manage_roles")
    email, phone = payload.get("email", "").strip(), payload.get("phone", "").strip()
    
    for key, val in [("payslip_email", email), ("payslip_phone", phone)]:
        row = await AppSetting.find_one(AppSetting.key == key)
        if row: row.value = val; await row.save()
        else: await AppSetting(key=key, value=val).insert()
    return {"email": email, "phone": phone}

# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════

async def _leave_to_dict(l: LeaveRecord, override_user: User = None) -> dict:
    user = override_user or await User.get(l.user_id)
    approver_name = None
    if l.approved_by:
        approver = await User.get(l.approved_by)
        approver_name = (approver.name or approver.email) if approver else None

    return {
        "id": str(l.id),
        "user_id": l.user_id,
        "start_date": l.start_date,
        "end_date": l.end_date,
        "leave_type": l.leave_type or "CASUAL",
        "day_type": getattr(l, "day_type", "FULL") or "FULL",
        "reason": l.reason,
        "status": l.status,
        "approved_by": l.approved_by,
        "remarks": getattr(l, "remarks", None),
        "user_name": (user.name or user.email) if user else None,
        "approver_name": approver_name,
    }

@router.delete("/salary/slip/{slip_id}", status_code=204, response_class=Response)
async def delete_salary_slip(slip_id: str, current_user: User = Depends(staff_checker)) -> Response:
    await _require_feature_access(current_user, "salary_manage_roles")
    slip = await SalarySlip.find_one(SalarySlip.id == slip_id, SalarySlip.is_deleted == False)
    if not slip: raise HTTPException(status_code=404, detail="Slip not found")
    
    policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
    if policy and policy.value == "HARD": await slip.delete()
    else: slip.is_deleted = True; await slip.save()
    return Response(status_code=204)