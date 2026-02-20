from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.employees.models import Employee
from app.modules.salary.models import LeaveRecord, SalarySlip, LeaveStatus
from app.modules.salary.schemas import (
    LeaveApplicationCreate, LeaveRecordRead, LeaveApproval,
    SalarySlipGenerate, SalarySlipRead
)

router = APIRouter()

# Role checkers
hr_checker = RoleChecker([UserRole.ADMIN]) # Assuming Admin acts as HR for now
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
    # Find employee profile
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(status_code=400, detail="Employee profile not found")

    db_leave = LeaveRecord(
        **leave_in.model_dump(),
        employee_id=employee.id,
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
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        return []
    return db.query(LeaveRecord).filter(LeaveRecord.employee_id == employee.id).all()

# SALARY ENDPOINTS
@router.post("/salary/generate", response_model=SalarySlipRead)
def generate_salary_slip(
    salary_in: SalarySlipGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(hr_checker)
) -> Any:
    employee = db.query(Employee).filter(Employee.id == salary_in.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Calculate Salary
    # Base Salary / 30 * (30 - UnpaidLeaves) - Deductions
    daily_wage = employee.base_salary / 30
    payable_days = 30 - salary_in.unpaid_leaves
    gross_salary = daily_wage * payable_days
    final_salary = gross_salary - salary_in.deduction_amount

    # Ensure no duplicate for month
    existing = db.query(SalarySlip).filter(
        SalarySlip.employee_id == salary_in.employee_id,
        SalarySlip.month == salary_in.month
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Salary slip for this month already exists")

    db_salary = SalarySlip(
        employee_id=salary_in.employee_id,
        month=salary_in.month,
        base_salary=employee.base_salary,
        paid_leaves=salary_in.paid_leaves,
        unpaid_leaves=salary_in.unpaid_leaves,
        deduction_amount=salary_in.deduction_amount,
        final_salary=round(final_salary, 2),
        generated_at=datetime.utcnow().date()
    )
    db.add(db_salary)
    db.commit()
    db.refresh(db_salary)
    return db_salary

@router.get("/salary/{employee_id}", response_model=List[SalarySlipRead])
def get_employee_salary_slips(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(hr_checker)
) -> Any:
    return db.query(SalarySlip).filter(SalarySlip.employee_id == employee_id).all()
