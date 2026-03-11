# backend/app/modules/salary/service.py
import calendar
from sqlalchemy.orm import Session
from sqlalchemy import extract
from fastapi import HTTPException
from datetime import datetime, UTC
from typing import List, Optional

from app.modules.salary.models import LeaveRecord, SalarySlip, LeaveStatus
from app.modules.salary.schemas import SalarySlipGenerate
from app.modules.users.models import User

PAID_LEAVE_LIMIT = 1  # 1 free paid leave per month


class SalaryService:
    def __init__(self, db: Session):
        self.db = db

    # ── Internal helpers ────────────────────────────────────────

    def _get_leave_data(self, user_id: int, year: int, month_num: int):
        """Fetch approved leaves for a user in given year/month."""
        approved_leaves = self.db.query(LeaveRecord).filter(
            LeaveRecord.user_id == user_id,
            LeaveRecord.status == LeaveStatus.APPROVED,
            extract('year', LeaveRecord.start_date) == year,
            extract('month', LeaveRecord.start_date) == month_num
        ).all()

        def _count_days(leave) -> float:
            """Calendar days, halved for HALF day_type."""
            raw = (leave.end_date - leave.start_date).days + 1
            if getattr(leave, 'day_type', 'FULL') == 'HALF':
                return raw * 0.5
            return float(raw)

        # UNPAID leave type always counts as unpaid regardless of paid limit
        unpaid_forced = sum(_count_days(l) for l in approved_leaves
                            if getattr(l, 'leave_type', '') == 'UNPAID')
        other_leaves = sum(_count_days(l) for l in approved_leaves
                           if getattr(l, 'leave_type', '') != 'UNPAID')
        paid_from_other = min(other_leaves, PAID_LEAVE_LIMIT)
        unpaid_from_other = max(0.0, other_leaves - PAID_LEAVE_LIMIT)

        total_leave_days = other_leaves + unpaid_forced
        paid_leaves = paid_from_other
        unpaid_leaves = unpaid_from_other + unpaid_forced
        return approved_leaves, total_leave_days, paid_leaves, unpaid_leaves

    def _get_incentive_data(self, user_id: int, month_str: str):
        """Fetch incentive and slab bonus from IncentiveSlip for the month.
        
        Incentive is only included if the slip was generated at least 10 days ago.
        This ensures the 7-day client refund window has passed before paying incentive.
        """
        from app.modules.incentives.models import IncentiveSlip
        from datetime import timedelta, date as date_type
        slip = self.db.query(IncentiveSlip).filter(
            IncentiveSlip.user_id == user_id,
            IncentiveSlip.period == month_str
        ).first()

        if not slip:
            return 0.0, 0.0

        # 10-day delay: incentive only included if generated 10+ days ago
        today = datetime.now(UTC).date()
        gen_dt = slip.generated_at
        if gen_dt is not None:
            gen_date = gen_dt.date() if hasattr(gen_dt, 'date') else gen_dt
            if (today - gen_date).days < 10:
                return 0.0, 0.0

        total = slip.total_incentive or 0.0
        # Slab bonus = total - (per_unit * achieved)
        slab_bonus = max(0.0, total - (slip.amount_per_unit or 0.0) * (slip.achieved or 0))
        incentive_only = total - slab_bonus
        return round(incentive_only, 2), round(slab_bonus, 2)

    def _compute_salary(self, base: float, unpaid_leaves: int, incentive_amount: float,
                        slab_bonus: float, extra_deduction: float):
        """Compute salary figures from inputs."""
        daily_wage = base / 30
        gross_salary = daily_wage * max(0, 30 - unpaid_leaves)
        leave_deduction = round(daily_wage * unpaid_leaves, 2)
        total_earnings = round(gross_salary + incentive_amount + slab_bonus, 2)
        final_salary = round(total_earnings - extra_deduction, 2)
        return {
            'daily_wage': daily_wage,
            'gross_salary': round(gross_salary, 2),
            'leave_deduction': leave_deduction,
            'total_earnings': total_earnings,
            'final_salary': final_salary,
        }

    def _format_slip(self, s: SalarySlip) -> dict:
        """Serialize a SalarySlip ORM object to a dict."""
        return {
            'id': s.id,
            'user_id': s.user_id,
            'month': s.month,
            'base_salary': s.base_salary,
            'paid_leaves': s.paid_leaves,
            'unpaid_leaves': s.unpaid_leaves,
            'deduction_amount': s.deduction_amount or 0.0,
            'incentive_amount': s.incentive_amount or 0.0,
            'slab_bonus': s.slab_bonus or 0.0,
            'total_earnings': s.total_earnings,
            'final_salary': s.final_salary,
            'status': s.status or 'CONFIRMED',
            'confirmed_by': s.confirmed_by,
            'confirmed_at': s.confirmed_at,
            'generated_at': s.generated_at,
            'user_name': (s.user.name or s.user.email) if s.user else f"User #{s.user_id}",
            'confirmer_name': (s.confirmer.name or s.confirmer.email) if s.confirmer else None,
        }

    # ── Public methods ───────────────────────────────────────────

    def preview_salary(self, user_id: int, month: str, extra_deduction: float = 0.0,
                        base_salary: Optional[float] = None) -> dict:
        """Return salary preview without saving to DB."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        year, month_num = map(int, month.split('-'))
        approved_leaves, total_leave_days, paid_leaves, unpaid_leaves = \
            self._get_leave_data(user_id, year, month_num)

        incentive_amount, slab_bonus = self._get_incentive_data(user_id, month)
        base = base_salary if base_salary is not None else (user.base_salary or 0.0)
        calc = self._compute_salary(base, unpaid_leaves, incentive_amount, slab_bonus, extra_deduction)

        existing = self.db.query(SalarySlip).filter(
            SalarySlip.user_id == user_id,
            SalarySlip.month == month
        ).first()

        return {
            "user_id": user_id,
            "user_name": user.name or user.email,
            "month": month,
            "base_salary": base,
            "working_days": max(0, 30 - unpaid_leaves),
            "total_leave_days": total_leave_days,
            "paid_leaves": paid_leaves,
            "unpaid_leaves": unpaid_leaves,
            "leave_deduction": calc['leave_deduction'],
            "incentive_amount": incentive_amount,
            "slab_bonus": slab_bonus,
            "extra_deduction": extra_deduction,
            "total_earnings": calc['total_earnings'],
            "final_salary": calc['final_salary'],
            "approved_leaves": [
                {
                    "id": l.id,
                    "start_date": str(l.start_date),
                    "end_date": str(l.end_date),
                    "leave_type": l.leave_type or "CASUAL",
                    "days": (l.end_date - l.start_date).days + 1,
                }
                for l in approved_leaves
            ],
            "has_existing_slip": existing is not None,
            "existing_slip_id": existing.id if existing else None,
            "existing_slip_status": existing.status if existing else None,
        }

    def generate_salary_slip(self, salary_in: SalarySlipGenerate) -> dict:
        """Generate a new DRAFT salary slip (auto-calculates leaves from DB)."""
        user = self.db.query(User).filter(User.id == salary_in.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prevent duplicates
        existing = self.db.query(SalarySlip).filter(
            SalarySlip.user_id == salary_in.user_id,
            SalarySlip.month == salary_in.month
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Salary slip for this month already exists"
            )

        year, month_num = map(int, salary_in.month.split('-'))
        approved_leaves, total_leave_days, paid_leaves, unpaid_leaves = \
            self._get_leave_data(salary_in.user_id, year, month_num)

        incentive_amount, slab_bonus = self._get_incentive_data(salary_in.user_id, salary_in.month)
        base = salary_in.base_salary if salary_in.base_salary is not None else (user.base_salary or 0.0)
        extra_deduction = salary_in.extra_deduction
        calc = self._compute_salary(base, unpaid_leaves, incentive_amount, slab_bonus, extra_deduction)

        db_salary = SalarySlip(
            user_id=salary_in.user_id,
            month=salary_in.month,
            base_salary=base,
            paid_leaves=paid_leaves,
            unpaid_leaves=unpaid_leaves,
            deduction_amount=extra_deduction,
            incentive_amount=incentive_amount,
            slab_bonus=slab_bonus,
            total_earnings=calc['total_earnings'],
            final_salary=calc['final_salary'],
            status="DRAFT",
            generated_at=datetime.now(UTC).date(),
        )
        self.db.add(db_salary)
        self.db.commit()
        self.db.refresh(db_salary)
        return self._format_slip(db_salary)

    def regenerate_salary_slip(self, salary_in: SalarySlipGenerate) -> dict:
        """Delete any existing slip (DRAFT or CONFIRMED) and create a fresh DRAFT."""
        existing = self.db.query(SalarySlip).filter(
            SalarySlip.user_id == salary_in.user_id,
            SalarySlip.month == salary_in.month
        ).first()
        if existing:
            self.db.delete(existing)
            self.db.commit()
        return self.generate_salary_slip(salary_in)

    def update_draft_slip(self, slip_id: int, salary_in: SalarySlipGenerate) -> dict:
        """Recalculate and update an existing DRAFT salary slip."""
        slip = self.db.query(SalarySlip).filter(SalarySlip.id == slip_id).first()
        if not slip:
            raise HTTPException(status_code=404, detail="Salary slip not found")
        if slip.status != "DRAFT":
            raise HTTPException(status_code=400, detail="Only DRAFT slips can be updated")

        user = self.db.query(User).filter(User.id == slip.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        year, month_num = map(int, slip.month.split('-'))
        approved_leaves, total_leave_days, paid_leaves, unpaid_leaves = \
            self._get_leave_data(slip.user_id, year, month_num)

        incentive_amount, slab_bonus = self._get_incentive_data(slip.user_id, slip.month)
        base = salary_in.base_salary if salary_in.base_salary is not None else (user.base_salary or 0.0)
        extra_deduction = salary_in.extra_deduction
        calc = self._compute_salary(base, unpaid_leaves, incentive_amount, slab_bonus, extra_deduction)

        slip.base_salary = base
        slip.paid_leaves = paid_leaves
        slip.unpaid_leaves = unpaid_leaves
        slip.deduction_amount = extra_deduction
        slip.incentive_amount = incentive_amount
        slip.slab_bonus = slab_bonus
        slip.total_earnings = calc['total_earnings']
        slip.final_salary = calc['final_salary']
        slip.generated_at = datetime.now(UTC).date()
        self.db.commit()
        self.db.refresh(slip)
        return self._format_slip(slip)

    def confirm_salary_slip(self, slip_id: int, confirmed_by_id: int) -> dict:
        """Confirm a DRAFT slip, making it visible to the employee."""
        slip = self.db.query(SalarySlip).filter(SalarySlip.id == slip_id).first()
        if not slip:
            raise HTTPException(status_code=404, detail="Salary slip not found")
        if slip.status != "DRAFT":
            raise HTTPException(status_code=400, detail="Only DRAFT slips can be confirmed")

        slip.status = "CONFIRMED"
        slip.confirmed_by = confirmed_by_id
        slip.confirmed_at = datetime.now(UTC).date()
        self.db.commit()
        self.db.refresh(slip)
        return self._format_slip(slip)

    def get_user_salary_slips(self, user_id: int, show_drafts: bool = True) -> List[dict]:
        """Get salary slips for a specific user."""
        query = self.db.query(SalarySlip).filter(SalarySlip.user_id == user_id)
        if not show_drafts:
            query = query.filter(SalarySlip.status == "CONFIRMED")
        slips = query.order_by(SalarySlip.month.desc()).all()
        return [self._format_slip(s) for s in slips]

    def get_all_salary_slips(self) -> List[dict]:
        """Get all salary slips (admin use)."""
        slips = self.db.query(SalarySlip).order_by(SalarySlip.month.desc()).all()
        return [self._format_slip(s) for s in slips]

    def generate_invoice_html(self, slip_id: int) -> str:
        """Generate a professional printable HTML payslip."""
        slip = self.db.query(SalarySlip).filter(SalarySlip.id == slip_id).first()
        if not slip:
            raise HTTPException(status_code=404, detail="Salary slip not found")

        user = slip.user
        slab_bonus = slip.slab_bonus or 0.0
        incentive_amount = slip.incentive_amount or 0.0
        daily_wage = slip.base_salary / 30
        leave_deduction = round(daily_wage * slip.unpaid_leaves, 2)
        extra_deduction = slip.deduction_amount or 0.0
        total_deductions = leave_deduction + extra_deduction
        gross_earnings = slip.total_earnings or slip.final_salary

        year, month_num = map(int, slip.month.split('-'))
        month_name = f"{calendar.month_name[month_num]} {year}"

        raw_date = slip.confirmed_at or slip.generated_at
        try:
            issue_date_str = raw_date.strftime("%d %B %Y")
        except Exception:
            issue_date_str = str(raw_date)

        emp_name = user.name or user.email
        designation = str(user.role).replace('_', ' ').title()

        # ------ amount in words (simple) ------
        def amount_in_words(amount: float) -> str:
            ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
                    "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
                    "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
            tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty",
                    "Sixty", "Seventy", "Eighty", "Ninety"]

            def below_thousand(n):
                if n == 0:
                    return ""
                elif n < 20:
                    return ones[n] + " "
                elif n < 100:
                    return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "") + " "
                else:
                    return ones[n // 100] + " Hundred " + below_thousand(n % 100)

            rupees = int(amount)
            paise = round((amount - rupees) * 100)
            if rupees == 0:
                return "Zero Rupees Only"
            result = ""
            if rupees >= 100000:
                result += below_thousand(rupees // 100000) + "Lakh "
                rupees %= 100000
            if rupees >= 1000:
                result += below_thousand(rupees // 1000) + "Thousand "
                rupees %= 1000
            result += below_thousand(rupees)
            result = result.strip() + " Rupees"
            if paise:
                result += f" and {below_thousand(paise).strip()} Paise"
            return result + " Only"

        net_in_words = amount_in_words(slip.final_salary)
        status_str = slip.status if isinstance(slip.status, str) else slip.status.value
        invoice_no = f"INV-{year}{calendar.month_name[month_num].lower()}-{slip.id}"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Salary Slip &mdash; {month_name}</title>
    <style>
        @page {{ size: A4; margin: 10mm 12mm; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Arial, Helvetica, sans-serif;
            background: #c8c8c8;
            color: #1a1a1a;
            font-size: 12px;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
        /* ── A4 Page ── */
        .a4-page {{
            width: 210mm;
            min-height: 297mm;
            background: #ffffff;
            margin: 20px auto;
            padding: 14mm 14mm 12mm;
            box-shadow: 0 4px 24px rgba(0,0,0,0.25);
        }}
        /* ── Header ── */
        .slip-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding-bottom: 14px;
            border-bottom: 2.5px solid #2d7a6e;
            margin-bottom: 14px;
        }}
        .logo-block {{ display: flex; align-items: center; gap: 12px; }}
        .logo-icon {{
            width: 56px; height: 56px;
            background: linear-gradient(135deg, #2d7a6e 0%, #1a4f46 100%);
            border-radius: 8px;
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            color: #fff; font-size: 20px; font-weight: 900;
            letter-spacing: -1px; flex-shrink: 0;
            line-height: 1;
        }}
        .logo-icon span {{ font-size: 8px; font-weight: 600; letter-spacing: 0.5px; margin-top: 2px; opacity: 0.9; }}
        .company-name-big {{ font-size: 17px; font-weight: 800; color: #1a1a1a; line-height: 1.25; }}
        .company-tagline {{ font-size: 10px; color: #666; letter-spacing: 0.5px; margin-top: 3px; }}
        .contact-block {{ text-align: right; font-size: 11.5px; color: #444; line-height: 2; }}
        .contact-block strong {{ color: #111; }}
        /* ── Invoice Meta ── */
        .invoice-meta {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            border: 1.5px solid #e2e8f0;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 14px;
        }}
        .meta-cell {{ padding: 10px 14px; border-right: 1px solid #e2e8f0; }}
        .meta-cell:last-child {{ border-right: none; }}
        .meta-label {{ font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 4px; font-weight: 600; }}
        .meta-value {{ font-size: 13px; font-weight: 700; color: #1a1a1a; word-break: break-word; }}
        .status-draft {{ color: #B45309; }}
        .status-confirmed {{ color: #059669; }}
        /* ── Employee Section ── */
        .section-box {{ border: 1.5px solid #e2e8f0; border-radius: 8px; overflow: hidden; margin-bottom: 14px; }}
        .section-header {{
            background: #2d7a6e; color: #fff;
            padding: 8px 14px; font-size: 11px;
            font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
        }}
        .emp-grid2 {{ display: grid; grid-template-columns: 1fr 1fr; }}
        .emp-col-l {{ border-right: 1px solid #e2e8f0; }}
        .emp-row2 {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 8px 14px; border-bottom: 1px solid #f1f5f9; font-size: 12px;
        }}
        .emp-row2:last-child {{ border-bottom: none; }}
        .emp-col-r .emp-row2:last-child {{ border-bottom: none; }}
        .emp-lbl {{ color: #666; font-weight: 500; }}
        .emp-val {{ font-weight: 700; color: #1a1a1a; text-align: right; max-width: 60%; word-break: break-word; }}
        /* ── Leave Chips ── */
        .leave-chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }}
        .lchip {{
            padding: 5px 13px; border-radius: 20px; font-size: 11.5px; font-weight: 600;
        }}
        .chip-b {{ background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }}
        .chip-g {{ background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; }}
        .chip-r {{ background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }}
        /* ── Salary Table ── */
        .salary-table {{ width: 100%; border-collapse: collapse; }}
        .salary-table thead th {{
            background: #f8fafc; padding: 8px 14px;
            font-size: 10.5px; color: #64748b;
            text-transform: uppercase; letter-spacing: 0.6px; font-weight: 700;
            text-align: left; border-bottom: 1.5px solid #e2e8f0;
        }}
        .salary-table thead th:last-child {{ text-align: right; }}
        .salary-table tbody td {{
            padding: 9px 14px; font-size: 12px;
            border-bottom: 1px solid #f1f5f9; color: #222;
        }}
        .salary-table tbody td:last-child {{ text-align: right; font-weight: 700; }}
        .salary-table tbody tr:last-child td {{ border-bottom: none; }}
        .salary-table tfoot td {{
            padding: 8px 14px; font-size: 12px; font-weight: 700;
            border-top: 2px solid #e2e8f0; background: #f8fafc;
        }}
        .salary-table tfoot td:last-child {{ text-align: right; }}
        /* ── Net Pay ── */
        .net-pay-bar {{
            background: linear-gradient(135deg, #2d7a6e 0%, #1a4f46 100%);
            color: #fff; border-radius: 8px;
            padding: 14px 18px;
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 18px;
        }}
        .net-words-lbl {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; opacity: 0.8; margin-bottom: 4px; }}
        .net-words {{ font-size: 12px; font-style: italic; max-width: 320px; }}
        .net-amount-lbl {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; opacity: 0.8; margin-bottom: 2px; text-align: right; }}
        .net-amount {{ font-size: 26px; font-weight: 900; text-align: right; }}
        /* ── Signatures ── */
        .sig-section {{
            display: grid; grid-template-columns: repeat(3, 1fr);
            gap: 20px; margin-bottom: 16px;
        }}
        .sig-block {{ text-align: center; }}
        .sig-line {{
            border-top: 1px solid #999;
            margin-top: 38px; padding-top: 5px;
            font-size: 10.5px; color: #666;
        }}
        /* ── Footer ── */
        .slip-footer {{
            text-align: center; font-size: 10px; color: #999;
            border-top: 1px solid #e2e8f0; padding-top: 10px;
        }}
        /* ── Print Bar ── */
        .print-bar {{
            width: 210mm; margin: 12px auto;
            display: flex; gap: 10px; justify-content: center;
        }}
        .btn-print {{
            padding: 10px 30px; background: #2d7a6e; color: #fff;
            border: none; font-size: 13px; font-weight: 700;
            cursor: pointer; font-family: inherit; border-radius: 6px;
        }}
        .btn-close-w {{
            padding: 10px 26px; background: #fff; color: #2d7a6e;
            border: 2px solid #2d7a6e; font-size: 13px; font-weight: 700;
            cursor: pointer; font-family: inherit; border-radius: 6px;
        }}
        @media print {{
            body {{ background: #fff; }}
            .a4-page {{ margin: 0; padding: 10mm 12mm; box-shadow: none; width: 100%; min-height: auto; }}
            .print-bar {{ display: none; }}
        }}
    </style>
</head>
<body>

<div class="a4-page">

    <!-- HEADER: Logo + Company + Contact -->
    <div class="slip-header">
        <div class="logo-block">
            <div class="logo-icon">HK<span>DIGI</span></div>
            <div>
                <div class="company-name-big">HK DigiVerse<br>&amp; IT Consultancy</div>
                <div class="company-tagline">Talent &nbsp;&middot;&nbsp; Property &nbsp;&middot;&nbsp; Fintech</div>
            </div>
        </div>
        <div class="contact-block">
            <div>Email: <strong>hrmangukiya3494@gmail.com</strong></div>
            <div>Contact No: <strong>8866005029</strong></div>
        </div>
    </div>

    <!-- INVOICE META -->
    <div class="invoice-meta">
        <div class="meta-cell">
            <div class="meta-label">Invoice No.</div>
            <div class="meta-value">{invoice_no}</div>
        </div>
        <div class="meta-cell">
            <div class="meta-label">Date</div>
            <div class="meta-value">{issue_date_str}</div>
        </div>
        <div class="meta-cell">
            <div class="meta-label">Payment Status</div>
            <div class="meta-value {'status-confirmed' if status_str == 'CONFIRMED' else 'status-draft'}">{status_str.lower()}</div>
        </div>
        <div class="meta-cell">
            <div class="meta-label">Total Amount</div>
            <div class="meta-value">&#8377; {slip.final_salary:,.2f}</div>
        </div>
    </div>

    <!-- EMPLOYEE DETAILS -->
    <div class="section-box">
        <div class="section-header">Employee Information</div>
        <div class="emp-grid2">
            <div class="emp-col-l">
                <div class="emp-row2">
                    <span class="emp-lbl">Name</span>
                    <span class="emp-val">{emp_name}</span>
                </div>
                <div class="emp-row2">
                    <span class="emp-lbl">Designation</span>
                    <span class="emp-val">{designation}</span>
                </div>
                <div class="emp-row2">
                    <span class="emp-lbl">Email</span>
                    <span class="emp-val">{user.email}</span>
                </div>
            </div>
            <div class="emp-col-r">
                <div class="emp-row2">
                    <span class="emp-lbl">Department</span>
                    <span class="emp-val">{user.department or '&mdash;'}</span>
                </div>
                <div class="emp-row2">
                    <span class="emp-lbl">Employee ID</span>
                    <span class="emp-val">EMP-{user.id:04d}</span>
                </div>
                <div class="emp-row2">
                    <span class="emp-lbl">Phone</span>
                    <span class="emp-val">{user.phone or '&mdash;'}</span>
                </div>
            </div>
        </div>
    </div>

    <!-- LEAVE SUMMARY CHIPS -->
    <div class="leave-chips">
        <div class="lchip chip-b">Pay Period: {month_name}</div>
        <div class="lchip chip-b">Working Days: {max(0, 30 - slip.unpaid_leaves)} / 30</div>
        <div class="lchip chip-g">Paid Leaves: {slip.paid_leaves}</div>
        <div class="lchip chip-r">Unpaid Leaves: {slip.unpaid_leaves}</div>
    </div>

    <!-- SALARY DETAILS TABLE -->
    <div class="section-box">
        <div class="section-header">Salary Details</div>
        <table class="salary-table">
            <thead>
                <tr>
                    <th>Description</th>
                    <th>Type</th>
                    <th>Amount (&#8377;)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Base Salary</td>
                    <td><span style="color:#2563EB;font-size:10.5px;font-weight:700;">EARNING</span></td>
                    <td>&#8377; {slip.base_salary:,.2f}</td>
                </tr>
                <tr>
                    <td>Performance Incentive</td>
                    <td><span style="color:#2563EB;font-size:10.5px;font-weight:700;">EARNING</span></td>
                    <td>&#8377; {incentive_amount:,.2f}</td>
                </tr>
                <tr>
                    <td>Slab Bonus</td>
                    <td><span style="color:#2563EB;font-size:10.5px;font-weight:700;">EARNING</span></td>
                    <td>&#8377; {slab_bonus:,.2f}</td>
                </tr>
                <tr>
                    <td>Leave Deduction &nbsp;<span style="font-size:10.5px;color:#888;">({slip.unpaid_leaves} unpaid day(s) @ &#8377;{daily_wage:,.2f}/day)</span></td>
                    <td><span style="color:#DC2626;font-size:10.5px;font-weight:700;">DEDUCTION</span></td>
                    <td style="color:#DC2626;">&#8722; &#8377; {leave_deduction:,.2f}</td>
                </tr>
                <tr>
                    <td>Other Deductions</td>
                    <td><span style="color:#DC2626;font-size:10.5px;font-weight:700;">DEDUCTION</span></td>
                    <td style="color:#DC2626;">&#8722; &#8377; {extra_deduction:,.2f}</td>
                </tr>
            </tbody>
            <tfoot>
                <tr>
                    <td>Gross Earnings</td>
                    <td></td>
                    <td style="color:#059669;">&#8377; {gross_earnings:,.2f}</td>
                </tr>
                <tr>
                    <td>Total Deductions</td>
                    <td></td>
                    <td style="color:#DC2626;">&#8377; {total_deductions:,.2f}</td>
                </tr>
            </tfoot>
        </table>
    </div>

    <!-- NET PAY -->
    <div class="net-pay-bar">
        <div>
            <div class="net-words-lbl">Net Salary in Words</div>
            <div class="net-words">{net_in_words}</div>
        </div>
        <div>
            <div class="net-amount-lbl">Net Amount Payable</div>
            <div class="net-amount">&#8377; {slip.final_salary:,.2f}</div>
        </div>
    </div>

    <!-- SIGNATURES -->
    <div class="sig-section">
        <div class="sig-block"><div class="sig-line">Employee Signature</div></div>
        <div class="sig-block"><div class="sig-line">HR / Payroll</div></div>
        <div class="sig-block"><div class="sig-line">Authorized Signatory</div></div>
    </div>

    <!-- FOOTER -->
    <div class="slip-footer">
        This is a computer-generated salary slip and does not require a physical signature.
        &nbsp;&middot;&nbsp; HK DigiVerse &amp; IT Consultancy &nbsp;&middot;&nbsp; Confidential &mdash; For Employee Use Only
    </div>

</div>

<div class="print-bar">
    <button class="btn-close-w" onclick="window.close()">&#10005; Close</button>
    <button class="btn-print" onclick="window.print()">&#128438; Print / Save as PDF</button>
</div>

</body>
</html>"""
        return html


