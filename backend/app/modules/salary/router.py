from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, UTC

from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.salary.models import LeaveRecord, SalarySlip, LeaveStatus
from app.modules.salary.schemas import (
    LeaveApplicationCreate, LeaveRecordRead, LeaveApproval,
    SalarySlipGenerate, SalarySlipRead
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

# LEAVE ENDPOINTS
@router.post("/leave", response_model=LeaveRecordRead)
def apply_leave(
    leave_in: LeaveApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    db_leave = LeaveRecord(
        **leave_in.model_dump(),
        user_id=current_user.id,
        status=LeaveStatus.PENDING
    )
    db.add(db_leave)
    db.commit()
    db.refresh(db_leave)
    return db_leave

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

    db.commit()
    db.refresh(db_leave)
    return db_leave

@router.get("/leave", response_model=List[LeaveRecordRead])
def get_my_leaves(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    leaves = db.query(LeaveRecord).filter(LeaveRecord.user_id == current_user.id).all()
    return [
        {
            "id": l.id,
            "user_id": l.user_id,
            "start_date": l.start_date,
            "end_date": l.end_date,
            "reason": l.reason,
            "status": l.status,
            "approved_by": l.approved_by,
            "user_name": current_user.name or current_user.email,
            "approver_name": (l.approver.name or l.approver.email) if l.approver else None,
        }
        for l in leaves
    ]

@router.get("/leave/all", response_model=List[LeaveRecordRead])
def get_all_leaves(
    db: Session = Depends(get_db),
    current_user: User = Depends(hr_checker)
) -> Any:
    leaves = db.query(LeaveRecord).all()
    return [
        {
            "id": l.id,
            "user_id": l.user_id,
            "start_date": l.start_date,
            "end_date": l.end_date,
            "reason": l.reason,
            "status": l.status,
            "approved_by": l.approved_by,
            "user_name": (l.user.name or l.user.email) if l.user else None,
            "approver_name": (l.approver.name or l.approver.email) if l.approver else None,
        }
        for l in leaves
    ]

# SALARY ENDPOINTS
@router.post("/salary/generate", response_model=SalarySlipRead)
def generate_salary_slip(
    salary_in: SalarySlipGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(hr_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    service = SalaryService(db)
    return service.generate_salary_slip(salary_in)

@router.get("/salary/me", response_model=List[SalarySlipRead])
def get_my_salary_slips(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    service = SalaryService(db)
    return service.get_user_salary_slips(current_user.id)

@router.get("/salary/{user_id}", response_model=List[SalarySlipRead])
def get_user_salary_slips(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(hr_checker)
) -> Any:
    from app.modules.salary.service import SalaryService
    service = SalaryService(db)
    return service.get_user_salary_slips(user_id)

