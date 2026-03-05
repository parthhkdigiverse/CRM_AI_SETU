from sqlalchemy.orm import Session
from sqlalchemy import extract
from fastapi import HTTPException
from datetime import datetime, UTC
from typing import List

from app.modules.salary.models import LeaveRecord, SalarySlip, LeaveStatus
from app.modules.salary.schemas import SalarySlipGenerate
from app.modules.users.models import User

class SalaryService:
    def __init__(self, db: Session):
        self.db = db

    def generate_salary_slip(self, salary_in: SalarySlipGenerate):
        user = self.db.query(User).filter(User.id == salary_in.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        year, month = map(int, salary_in.month.split('-'))

        # Calculate leaves
        approved_leaves = self.db.query(LeaveRecord).filter(
            LeaveRecord.user_id == user.id,
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

        # Calculate Salary: Base / 30 * (30 - UnpaidLeaves)
        base = user.base_salary or 0.0
        daily_wage = base / 30
        payable_days = max(0, 30 - unpaid_leaves)
        gross_salary = daily_wage * payable_days
        final_salary = gross_salary - salary_in.deduction_amount

        # Ensure no duplicate for month
        existing = self.db.query(SalarySlip).filter(
            SalarySlip.user_id == salary_in.user_id,
            SalarySlip.month == salary_in.month
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Salary slip for this month already exists")

        db_salary = SalarySlip(
            user_id=salary_in.user_id,
            month=salary_in.month,
            base_salary=base,
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

    def get_user_salary_slips(self, user_id: int):
        try:
            return self.db.query(SalarySlip).filter(SalarySlip.user_id == user_id).all()
        except Exception as e:
            print(f"Error fetching salary slips: {e}")
            return []

