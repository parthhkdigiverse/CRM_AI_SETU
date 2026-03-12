# backend/app/modules/salary/router.py
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, UTC

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


# ═══════════════════════════════════════════════════════
# LEAVE ENDPOINTS
# ═══════════════════════════════════════════════════════

@router.post("/leave", response_model=LeaveRecordRead)
def apply_leave(
    leave_in: LeaveApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
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
    current_user: User = Depends(hr_checker)
) -> Any:
    db_leave = db.query(LeaveRecord).filter(LeaveRecord.id == leave_id).first()
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
        LeaveRecord.user_id == current_user.id
    ).order_by(LeaveRecord.start_date.desc()).all()
    return [_leave_to_dict(l) for l in leaves]


@router.get("/leave/all", response_model=List[LeaveRecordRead])
def get_all_leaves(
    db: Session = Depends(get_db),
    current_user: User = Depends(hr_checker)
) -> Any:
    leaves = db.query(LeaveRecord).order_by(LeaveRecord.start_date.desc()).all()
    return [_leave_to_dict(l) for l in leaves]


@router.get("/leave/summary/{user_id}")
def get_leave_summary(
    user_id: int,
    month: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """Return leave counts for a user in the given month."""
    from sqlalchemy import extract
    year, month_num = map(int, month.split('-'))
    leaves = db.query(LeaveRecord).filter(
        LeaveRecord.user_id == user_id,
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
    current_user: User = Depends(hr_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    return SalaryService(db).preview_salary(user_id, month, extra_deduction, base_salary=base_salary)


@router.post("/salary/generate")
def generate_salary_slip(
    salary_in: SalarySlipGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(hr_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    return SalaryService(db).generate_salary_slip(salary_in)


@router.post("/salary/regenerate")
def regenerate_salary_slip(
    salary_in: SalarySlipGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(hr_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    return SalaryService(db).regenerate_salary_slip(salary_in)


@router.patch("/salary/update-draft/{slip_id}")
def update_draft_salary_slip(
    slip_id: int,
    salary_in: SalarySlipGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(hr_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    return SalaryService(db).update_draft_slip(slip_id, salary_in)


@router.patch("/salary/confirm/{slip_id}")
def confirm_salary_slip(
    slip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(hr_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    return SalaryService(db).confirm_salary_slip(slip_id, current_user.id)


@router.get("/salary/all")
def get_all_salary_slips(
    db: Session = Depends(get_db),
    current_user: User = Depends(hr_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    return SalaryService(db).get_all_salary_slips()


@router.get("/salary/me")
def get_my_salary_slips(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    # Non-admins only see CONFIRMED slips
    return SalaryService(db).get_user_salary_slips(current_user.id, show_drafts=False)


@router.get("/salary/{user_id}")
def get_user_salary_slips(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(hr_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    return SalaryService(db).get_user_salary_slips(user_id)


@router.get("/salary/slip/{slip_id}/invoice")
def get_salary_invoice(
    slip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    from fastapi.responses import HTMLResponse

    slip = db.query(SalarySlip).filter(SalarySlip.id == slip_id).first()
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
    current_user: User = Depends(hr_checker)
) -> Any:
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
    }

