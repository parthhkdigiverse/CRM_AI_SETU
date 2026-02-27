from sqlalchemy.orm import Session
from sqlalchemy import extract
from fastapi import HTTPException
from datetime import datetime, UTC
from typing import List

from app.modules.salary.models import LeaveRecord, SalarySlip, LeaveStatus
from app.modules.salary.schemas import SalarySlipGenerate
from app.modules.employees.models import Employee

class SalaryService:
    def __init__(self, db: Session):
        self.db = db

    def generate_salary_slip(self, salary_in: SalarySlipGenerate):
        employee = self.db.query(Employee).filter(Employee.id == salary_in.employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")

        year, month = map(int, salary_in.month.split('-'))
        
        # Calculate leaves
        approved_leaves = self.db.query(LeaveRecord).filter(
            LeaveRecord.employee_id == employee.id,
            LeaveRecord.status == LeaveStatus.APPROVED,
            extract('year', LeaveRecord.start_date) == year,
            extract('month', LeaveRecord.start_date) == month
        ).all()
        
        total_leave_days = 0
        for leave in approved_leaves:
            days = (leave.end_date - leave.start_date).days + 1
            total_leave_days += max(0, days)
            
        PAID_LEAVE_LIMIT = 1
        paid_leaves = min(total_leave_days, PAID_LEAVE_LIMIT)
        unpaid_leaves = max(0, total_leave_days - PAID_LEAVE_LIMIT)

        # Calculate Salary
        # Base Salary / 30 * (30 - UnpaidLeaves)
        daily_wage = employee.base_salary / 30
        payable_days = max(0, 30 - unpaid_leaves)
        gross_salary = daily_wage * payable_days
        
        final_salary = gross_salary - salary_in.deduction_amount

        # Ensure no duplicate for month
        existing = self.db.query(SalarySlip).filter(
            SalarySlip.employee_id == salary_in.employee_id,
            SalarySlip.month == salary_in.month
        ).first()
        
        if existing:
            # Update existing or raise error. Requirement says "already exists" error in router.
            raise HTTPException(status_code=400, detail="Salary slip for this month already exists")

        db_salary = SalarySlip(
            employee_id=salary_in.employee_id,
            month=salary_in.month,
            base_salary=employee.base_salary,
            paid_leaves=paid_leaves,
            unpaid_leaves=unpaid_leaves,
            deduction_amount=salary_in.deduction_amount,
            final_salary=round(final_salary, 2),
            generated_at=datetime.now(UTC).date()
        )
        self.db.add(db_salary)
        self.db.commit()
        self.db.refresh(db_salary)
        return db_salary

    def get_employee_salary_slips(self, employee_id: int):
        return self.db.query(SalarySlip).filter(SalarySlip.employee_id == employee_id).all()
