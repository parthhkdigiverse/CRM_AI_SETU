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
        
        # Fetch Incentive for this month
        from app.modules.incentives.models import IncentiveSlip
        incentive_slip = self.db.query(IncentiveSlip).filter(
            IncentiveSlip.user_id == user.id,
            IncentiveSlip.period == salary_in.month
        ).first()
        
        incentive_amount = incentive_slip.total_incentive if incentive_slip else 0.0
        total_earnings = gross_salary + incentive_amount
        final_salary = total_earnings - salary_in.deduction_amount

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
            incentive_amount=incentive_amount,
            total_earnings=round(total_earnings, 2),
            final_salary=round(final_salary, 2),
            generated_at=datetime.now(UTC).date()
        )
        self.db.add(db_salary)
        self.db.commit()
        self.db.refresh(db_salary)
        return db_salary

    def get_user_salary_slips(self, user_id: int):
        try:
            slips = self.db.query(SalarySlip).filter(SalarySlip.id > 0) # Placeholder or correct filter
            if user_id:
                slips = slips.filter(SalarySlip.user_id == user_id)
            
            results = slips.all()
            for s in results:
                if s.user:
                    s.user_name = s.user.name or s.user.email
            return results
        except Exception as e:
            print(f"Error fetching salary slips: {e}")
            return []

    def generate_invoice_html(self, slip_id: int):
        slip = self.db.query(SalarySlip).filter(SalarySlip.id == slip_id).first()
        if not slip:
            raise HTTPException(status_code=404, detail="Salary slip not found")
        
        user = slip.user
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', sans-serif; color: #1e293b; margin: 0; padding: 40px; background: #f8fafc; }}
                .invoice-card {{ background: white; max-width: 800px; margin: auto; padding: 50px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }}
                .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #f1f5f9; padding-bottom: 30px; margin-bottom: 30px; }}
                .logo-text {{ font-size: 24px; font-weight: 800; color: #4f46e5; letter-spacing: -1px; }}
                .invoice-title {{ font-size: 32px; font-weight: 700; color: #0f172a; margin: 0; }}
                .meta-row {{ display: flex; gap: 40px; margin-bottom: 40px; }}
                .meta-col h6 {{ margin: 0 0 8px; font-size: 12px; text-transform: uppercase; color: #94a3b8; letter-spacing: 1px; }}
                .meta-col p {{ margin: 0; font-weight: 600; color: #334155; }}
                .details-table {{ w-100; border-collapse: collapse; margin-bottom: 30px; }}
                .details-table th {{ text-align: left; padding: 12px; border-bottom: 1px solid #e2e8f0; color: #64748b; font-size: 13px; font-weight: 600; }}
                .details-table td {{ padding: 16px 12px; border-bottom: 1px solid #f1f5f9; font-size: 15px; }}
                .summary-row {{ display: flex; justify-content: flex-end; margin-top: 20px; }}
                .summary-box {{ background: #f1f5f9; padding: 25px; border-radius: 12px; width: 300px; }}
                .summary-line {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
                .summary-line.total {{ margin-top: 15px; padding-top: 15px; border-top: 2px solid #cbd5e1; font-size: 18px; font-weight: 800; color: #1e293b; }}
                .footer {{ text-align: center; margin-top: 50px; color: #94a3b8; font-size: 12px; border-top: 1px solid #f1f5f9; padding-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="invoice-card">
                <div class="header">
                    <div>
                        <div class="logo-text">SRM AI SETU</div>
                        <p style="margin:5px 0; font-size: 13px; color:#64748b;">Premium CRM Solutions</p>
                    </div>
                    <div style="text-align: right;">
                        <h1 class="invoice-title">PAYSLIP</h1>
                        <p style="color:#64748b; margin-top:5px;">#{slip.id}-{slip.month}</p>
                    </div>
                </div>

                <div class="meta-row">
                    <div class="meta-col">
                        <h6>Employee</h6>
                        <p>{user.name or user.email}</p>
                    </div>
                    <div class="meta-col">
                        <h6>Designation</h6>
                        <p>{user.role}</p>
                    </div>
                    <div class="meta-col">
                        <h6>Period</h6>
                        <p>{slip.month}</p>
                    </div>
                    <div class="meta-col">
                        <h6>Issue Date</h6>
                        <p>{slip.generated_at}</p>
                    </div>
                </div>

                <table style="width:100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background:#f8fafc;">
                            <th style="text-align:left; padding:12px; border-bottom:1px solid #e2e8f0;">Description</th>
                            <th style="text-align:right; padding:12px; border-bottom:1px solid #e2e8f0;">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding:16px 12px; border-bottom:1px solid #f1f5f9;">Basic Salary</td>
                            <td style="padding:16px 12px; border-bottom:1px solid #f1f5f9; text-align:right;">₹{slip.base_salary:,.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding:16px 12px; border-bottom:1px solid #f1f5f9;">
                                Calculated Incentive 
                                <small style="display:block; color:#94a3b8;">Based on monthly targets achieved</small>
                            </td>
                            <td style="padding:16px 12px; border-bottom:1px solid #f1f5f9; text-align:right;">₹{slip.incentive_amount:,.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding:16px 12px; border-bottom:1px solid #f1f5f9;">
                                Deductions
                                <small style="display:block; color:#94a3b8;">Unpaid Leaves: {slip.unpaid_leaves} days</small>
                            </td>
                            <td style="padding:16px 12px; border-bottom:1px solid #f1f5f9; text-align:right; color:#ef4444;">- ₹{slip.deduction_amount:,.2f}</td>
                        </tr>
                    </tbody>
                </table>

                <div class="summary-row">
                    <div class="summary-box">
                        <div class="summary-line">
                            <span>Gross Earnings</span>
                            <span>₹{slip.total_earnings:,.2f}</span>
                        </div>
                        <div class="summary-line">
                            <span>Total Deductions</span>
                            <span style="color:#ef4444;">- ₹{slip.deduction_amount:,.2f}</span>
                        </div>
                        <div class="summary-line total">
                            <span>NET PAYABLE</span>
                            <span>₹{slip.final_salary:,.2f}</span>
                        </div>
                    </div>
                </div>

                <div class="footer">
                    <p>Building the Future of CRM Integration</p>
                    <p>© 2026 SRM AI SETU. This is a computer-generated document and requires no signature.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html

