# backend/app/modules/salary/router.py
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from datetime import datetime, UTC
import json

from app.core.database import get_db
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
    allowed = _get_feature_roles(db, feature_key)
    if role_name not in allowed:
        raise HTTPException(status_code=403, detail=detail)


# ═══════════════════════════════════════════════════════
# LEAVE ENDPOINTS
# ═══════════════════════════════════════════════════════

@router.post("/leave", response_model=LeaveRecordRead)
def apply_leave(
    leave_in: LeaveApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin cannot apply leave")

    _require_feature_access(db, current_user, "leave_apply_roles", "You do not have permission to apply leave")

    if leave_in.end_date < leave_in.start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    db_leave = LeaveRecord(
        user_id=current_user.id,
        start_date=leave_in.start_date,
        end_date=leave_in.end_date,
        leave_type=leave_in.leave_type,
        day_type=leave_in.day_type,
        reason=leave_in.reason,
        status=LeaveStatus.PENDING,
    )
    db.add(db_leave)
    db.commit()
    db.refresh(db_leave)
    return _leave_to_dict(db_leave, current_user)


@router.patch("/leave/{leave_id}/approve", response_model=LeaveRecordRead)
def approve_leave(
    leave_id: int,
    approval_in: LeaveApproval,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "leave_manage_roles", "You do not have permission to approve/reject leave")

    db_leave = db.query(LeaveRecord).filter(LeaveRecord.id == leave_id, LeaveRecord.is_deleted == False).first()
    if not db_leave:
        raise HTTPException(status_code=404, detail="Leave record not found")

    db_leave.status = approval_in.status
    if approval_in.status == LeaveStatus.APPROVED:
        db_leave.approved_by = current_user.id
    if approval_in.remarks is not None:
        db_leave.remarks = approval_in.remarks.strip() or None

    db.commit()
    db.refresh(db_leave)
    return _leave_to_dict(db_leave)


@router.get("/leave", response_model=List[LeaveRecordRead])
def get_my_leaves(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    leaves = db.query(LeaveRecord).filter(
        LeaveRecord.user_id == current_user.id,
        LeaveRecord.is_deleted == False
    ).order_by(LeaveRecord.start_date.desc()).all()
    return [_leave_to_dict(l) for l in leaves]


@router.get("/leave/all", response_model=List[LeaveRecordRead])
def get_all_leaves(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "leave_manage_roles", "You do not have permission to view all leave records")

    leaves = db.query(LeaveRecord).filter(LeaveRecord.is_deleted == False).order_by(LeaveRecord.start_date.desc()).all()
    return [_leave_to_dict(l) for l in leaves]


@router.patch("/leave/{leave_id}", response_model=LeaveRecordRead)
def update_my_leave(
    leave_id: int,
    leave_in: LeaveApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "leave_edit_own_roles", "You do not have permission to edit leave")

    db_leave = db.query(LeaveRecord).filter(LeaveRecord.id == leave_id, LeaveRecord.is_deleted == False).first()
    if not db_leave:
        raise HTTPException(status_code=404, detail="Leave record not found")
    if db_leave.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can edit only your own leave")
    if db_leave.status != LeaveStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending leave can be edited")
    if leave_in.end_date < leave_in.start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    db_leave.start_date = leave_in.start_date
    db_leave.end_date = leave_in.end_date
    db_leave.leave_type = leave_in.leave_type
    db_leave.day_type = leave_in.day_type
    db_leave.reason = leave_in.reason
    db.commit()
    db.refresh(db_leave)
    return _leave_to_dict(db_leave, current_user)


@router.get("/leave/summary/{user_id}")
def get_leave_summary(
    user_id: int,
    month: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """Return leave counts for a user in the given month."""
    if current_user.role != UserRole.ADMIN and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    from sqlalchemy import extract
    year, month_num = map(int, month.split('-'))
    leaves = db.query(LeaveRecord).filter(
        LeaveRecord.user_id == user_id,
        LeaveRecord.is_deleted == False,
        extract('year', LeaveRecord.start_date) == year,
        extract('month', LeaveRecord.start_date) == month_num
    ).all()

    total = 0
    approved = 0
    pending = 0
    rejected = 0
    for l in leaves:
        days = (l.end_date - l.start_date).days + 1
        total += days
        if l.status == LeaveStatus.APPROVED:
            approved += days
        elif l.status == LeaveStatus.PENDING:
            pending += days
        else:
            rejected += days

    paid = min(approved, 1)
    unpaid = max(0, approved - 1)
    return {
        "user_id": user_id,
        "month": month,
        "total_leave_days": total,
        "approved_days": approved,
        "pending_days": pending,
        "rejected_days": rejected,
        "paid_leaves": paid,
        "unpaid_leaves": unpaid,
    }

@router.delete("/leave/{leave_id}", status_code=204, response_class=Response)
def delete_leave(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Response:
    leave = db.query(LeaveRecord).filter(LeaveRecord.id == leave_id, LeaveRecord.is_deleted == False).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")

    role_name = _current_role_name(current_user).upper()
    can_manage = role_name in _get_feature_roles(db, "leave_manage_roles")
    can_cancel_own = role_name in _get_feature_roles(db, "leave_cancel_own_roles")

    if can_manage:
        policy = db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
        is_hard = policy and policy.value == "HARD"

        if is_hard:
            db.delete(leave)
        else:
            leave.is_deleted = True
        db.commit()
        return Response(status_code=204)

    if not can_cancel_own:
        raise HTTPException(status_code=403, detail="You do not have permission to cancel leave")
    if leave.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can cancel only your own leave")
    if leave.status != LeaveStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending leave can be cancelled")

    leave.is_deleted = True
    db.commit()
    return Response(status_code=204)


# ═══════════════════════════════════════════════════════
# SALARY ENDPOINTS
# ═══════════════════════════════════════════════════════

@router.get("/salary/preview")
def preview_salary(
    user_id: int = Query(...),
    month: str = Query(...),
    extra_deduction: float = Query(0.0),
    base_salary: float = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "salary_manage_roles", "You do not have permission to preview salary")

    from app.modules.salary.service import SalaryService
    return SalaryService(db).preview_salary(user_id, month, extra_deduction, base_salary=base_salary)


@router.post("/salary/generate")
def generate_salary_slip(
    salary_in: SalarySlipGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "salary_manage_roles", "You do not have permission to generate salary")

    from app.modules.salary.service import SalaryService
    return SalaryService(db).generate_salary_slip(salary_in)


@router.post("/salary/regenerate")
def regenerate_salary_slip(
    salary_in: SalarySlipGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "salary_manage_roles", "You do not have permission to regenerate salary")

    from app.modules.salary.service import SalaryService
    return SalaryService(db).regenerate_salary_slip(salary_in)


@router.patch("/salary/update-draft/{slip_id}")
def update_draft_salary_slip(
    slip_id: int,
    salary_in: SalarySlipGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "salary_manage_roles", "You do not have permission to update draft salary")

    from app.modules.salary.service import SalaryService
    return SalaryService(db).update_draft_slip(slip_id, salary_in)


@router.patch("/salary/confirm/{slip_id}")
def confirm_salary_slip(
    slip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "salary_manage_roles", "You do not have permission to confirm salary")

    from app.modules.salary.service import SalaryService
    return SalaryService(db).confirm_salary_slip(slip_id, current_user.id)


@router.get("/salary/all")
def get_all_salary_slips(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "salary_view_all_roles", "You do not have permission to view all salary slips")

    from app.modules.salary.service import SalaryService
    return SalaryService(db).get_all_salary_slips()


@router.get("/salary/me")
def get_my_salary_slips(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    # Non-admins only see CONFIRMED slips
    return SalaryService(db).get_user_salary_slips(current_user.id, show_drafts=False, only_visible=True)


@router.get("/salary/{user_id}")
def get_user_salary_slips(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "salary_view_all_roles", "You do not have permission to view this employee salary slips")

    from app.modules.salary.service import SalaryService
    return SalaryService(db).get_user_salary_slips(user_id)


@router.patch("/salary/slip/{slip_id}/remarks")
def update_salary_slip_remarks(
    slip_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    slip = db.query(SalarySlip).filter(SalarySlip.id == slip_id, SalarySlip.is_deleted == False).first()
    if not slip:
        raise HTTPException(status_code=404, detail="Slip not found")

    can_manage = _current_role_name(current_user).upper() in _get_feature_roles(db, "salary_manage_roles")
    employee_remarks = payload.get("employee_remarks")
    manager_remarks = payload.get("manager_remarks")

    if can_manage:
        if employee_remarks is not None:
            slip.employee_remarks = str(employee_remarks).strip() or None
        if manager_remarks is not None:
            slip.manager_remarks = str(manager_remarks).strip() or None
    else:
        if slip.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You can update remarks only for your own salary slip")
        if slip.status != "CONFIRMED" or not getattr(slip, "is_visible_to_employee", True):
            raise HTTPException(status_code=400, detail="Remarks can be added only on visible confirmed slips")
        if employee_remarks is None:
            raise HTTPException(status_code=400, detail="employee_remarks is required")
        slip.employee_remarks = str(employee_remarks).strip() or None

    db.commit()
    db.refresh(slip)
    from app.modules.salary.service import SalaryService
    return SalaryService(db)._format_slip(slip)


@router.patch("/salary/slip/{slip_id}/visibility")
def update_salary_slip_visibility(
    slip_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "salary_manage_roles", "You do not have permission to change salary visibility")
    slip = db.query(SalarySlip).filter(SalarySlip.id == slip_id, SalarySlip.is_deleted == False).first()
    if not slip:
        raise HTTPException(status_code=404, detail="Slip not found")

    is_visible = bool(payload.get("is_visible_to_employee", False))
    slip.is_visible_to_employee = is_visible
    db.commit()
    db.refresh(slip)
    from app.modules.salary.service import SalaryService
    return SalaryService(db)._format_slip(slip)


@router.get("/salary/slip/{slip_id}/invoice")
def get_salary_invoice(
    slip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    from fastapi.responses import HTMLResponse

    slip = db.query(SalarySlip).filter(SalarySlip.id == slip_id, SalarySlip.is_deleted == False).first()
    if not slip:
        raise HTTPException(status_code=404, detail="Slip not found")

    if current_user.role != UserRole.ADMIN and slip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Non-admins can only view invoices for CONFIRMED slips
    if current_user.role != UserRole.ADMIN and slip.status != "CONFIRMED":
        raise HTTPException(status_code=403, detail="Slip not yet confirmed")

    html = SalaryService(db).generate_invoice_html(slip_id)
    return HTMLResponse(content=html)


# ═══════════════════════════════════════════════════════
# PAYSLIP COMPANY SETTINGS (admin configurable)
# ═══════════════════════════════════════════════════════

DEFAULT_PAYSLIP_EMAIL = "hrmangukiya3494@gmail.com"
DEFAULT_PAYSLIP_PHONE = "8866005029"


@router.get("/payslip-settings")
def get_payslip_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    email_row = db.query(AppSetting).filter(AppSetting.key == "payslip_email").first()
    phone_row = db.query(AppSetting).filter(AppSetting.key == "payslip_phone").first()
    return {
        "email": email_row.value if email_row else DEFAULT_PAYSLIP_EMAIL,
        "phone": phone_row.value if phone_row else DEFAULT_PAYSLIP_PHONE,
    }


@router.put("/payslip-settings")
def update_payslip_settings(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "salary_manage_roles", "You do not have permission to update payslip settings")

    email = (payload.get("email") or "").strip()
    phone = (payload.get("phone") or "").strip()
    if not email or not phone:
        raise HTTPException(status_code=400, detail="Email and phone are required")

    for key, val in [("payslip_email", email), ("payslip_phone", phone)]:
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row:
            row.value = val
        else:
            db.add(AppSetting(key=key, value=val))
    db.commit()
    return {"email": email, "phone": phone}


@router.get("/delete-policy")
def get_delete_policy(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> dict:
    _require_feature_access(db, current_user, "salary_manage_roles", "You do not have permission to view delete policy")

    row = db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
    return {"policy": row.value if row else "SOFT"}


@router.put("/delete-policy")
def update_delete_policy(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> dict:
    _require_feature_access(db, current_user, "salary_manage_roles", "You do not have permission to update delete policy")

    policy = payload.get("policy")
    if policy not in ["SOFT", "HARD"]:
        raise HTTPException(status_code=400, detail="Invalid policy type. Must be SOFT or HARD.")
    
    row = db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
    if row:
        row.value = policy
    else:
        db.add(AppSetting(key="delete_policy", value=policy))
    db.commit()
    return {"policy": policy}


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════

def _leave_to_dict(l: LeaveRecord, override_user: User = None) -> dict:
    user = override_user or l.user
    return {
        "id": l.id,
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
        "approver_name": (l.approver.name or l.approver.email) if l.approver else None,
        "created_at": l.created_at,
        "updated_at": l.updated_at,
    }

@router.delete("/salary/slip/{slip_id}", status_code=204, response_class=Response)
def delete_salary_slip(
    slip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Response:
    _require_feature_access(db, current_user, "salary_manage_roles", "You do not have permission to delete salary slips")

    slip = db.query(SalarySlip).filter(SalarySlip.id == slip_id, SalarySlip.is_deleted == False).first()
    if not slip:
        raise HTTPException(status_code=404, detail="Slip not found")
        
    policy = db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
    is_hard = policy and policy.value == "HARD"

    if is_hard:
        db.delete(slip)
    else:
        slip.is_deleted = True
    db.commit()
    return Response(status_code=204)

