# backend/app/modules/salary/service.py
import calendar
import os
from fastapi import HTTPException
from datetime import datetime, UTC, timedelta
from typing import List, Optional

from app.modules.salary.models import LeaveRecord, SalarySlip, LeaveStatus, AppSetting
from app.modules.salary.schemas import SalarySlipGenerate
from app.modules.users.models import User

PAID_LEAVE_LIMIT = 1  # 1 free paid leave per month


class SalaryService:

    # ── Internal helpers ────────────────────────────────────────

    async def _get_leave_data(self, user_id: str, year: int, month_num: int):
        """Fetch approved leaves for a user in given year/month."""
        all_leaves = await LeaveRecord.find(
            LeaveRecord.user_id == user_id,
            LeaveRecord.status == LeaveStatus.APPROVED,
            LeaveRecord.is_deleted == False
        ).to_list()

        # Filter by year/month in Python (MongoDB doesn't have extract())
        approved_leaves = [
            l for l in all_leaves
            if l.start_date.year == year and l.start_date.month == month_num
        ]

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

    async def _get_incentive_data(self, user_id: str, month_str: str):
        """Fetch incentive and slab bonus from IncentiveSlip for the month.
        
        Incentive is only included if the slip was generated at least 10 days ago.
        This ensures the 7-day client refund window has passed before paying incentive.
        """
        from app.modules.incentives.models import IncentiveSlip
        slip = await IncentiveSlip.find_one(
            IncentiveSlip.user_id == int(user_id) if user_id.isdigit() else None,
            IncentiveSlip.period == month_str
        )

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

    async def _format_slip(self, s: SalarySlip) -> dict:
        """Serialize a SalarySlip Beanie document to a dict."""
        user = await User.find_one(User.id == int(s.user_id)) if s.user_id else None
        confirmer = await User.find_one(User.id == int(s.confirmed_by)) if s.confirmed_by else None

        return {
            'id': str(s.id),
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
            'is_visible_to_employee': bool(getattr(s, 'is_visible_to_employee', True)),
            'employee_remarks': getattr(s, 'employee_remarks', None),
            'manager_remarks': getattr(s, 'manager_remarks', None),
            'generated_at': s.generated_at,
            'user_name': (user.name or user.email) if user else f"User #{s.user_id}",
            'confirmer_name': (confirmer.name or confirmer.email) if confirmer else None,
        }

    # ── Public methods ───────────────────────────────────────────

    async def preview_salary(self, user_id: str, month: str, extra_deduction: float = 0.0,
                        base_salary: Optional[float] = None) -> dict:
        """Return salary preview without saving to DB."""
        user = await User.find_one(User.id == int(user_id)) if str(user_id).isdigit() else None
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        year, month_num = map(int, month.split('-'))
        approved_leaves, total_leave_days, paid_leaves, unpaid_leaves = \
            await self._get_leave_data(str(user_id), year, month_num)

        incentive_amount, slab_bonus = await self._get_incentive_data(str(user_id), month)
        base = base_salary if base_salary is not None else (user.base_salary or 0.0)
        calc = self._compute_salary(base, unpaid_leaves, incentive_amount, slab_bonus, extra_deduction)

        existing = await SalarySlip.find_one(
            SalarySlip.user_id == str(user_id),
            SalarySlip.month == month,
            SalarySlip.is_deleted == False
        )

        return {
            "user_id": str(user_id),
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
                    "id": str(l.id),
                    "start_date": str(l.start_date),
                    "end_date": str(l.end_date),
                    "leave_type": l.leave_type or "CASUAL",
                    "days": (l.end_date - l.start_date).days + 1,
                }
                for l in approved_leaves
            ],
            "has_existing_slip": existing is not None,
            "existing_slip_id": str(existing.id) if existing else None,
            "existing_slip_status": existing.status if existing else None,
        }

    async def generate_salary_slip(self, salary_in: SalarySlipGenerate) -> dict:
        """Generate a new DRAFT salary slip (auto-calculates leaves from DB)."""
        uid = str(salary_in.user_id)
        user = await User.find_one(User.id == int(uid)) if uid.isdigit() else None
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prevent duplicates
        existing = await SalarySlip.find_one(
            SalarySlip.user_id == uid,
            SalarySlip.month == salary_in.month
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Salary slip for this month already exists"
            )

        year, month_num = map(int, salary_in.month.split('-'))
        approved_leaves, total_leave_days, paid_leaves, unpaid_leaves = \
            await self._get_leave_data(uid, year, month_num)

        incentive_amount, slab_bonus = await self._get_incentive_data(uid, salary_in.month)
        base = salary_in.base_salary if salary_in.base_salary is not None else (user.base_salary or 0.0)
        extra_deduction = salary_in.extra_deduction
        calc = self._compute_salary(base, unpaid_leaves, incentive_amount, slab_bonus, extra_deduction)

        db_salary = SalarySlip(
            user_id=uid,
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
            is_visible_to_employee=False,
            generated_at=datetime.now(UTC),
        )
        await db_salary.insert()
        return await self._format_slip(db_salary)

    async def regenerate_salary_slip(self, salary_in: SalarySlipGenerate) -> dict:
        """Delete any existing slip (DRAFT or CONFIRMED) and create a fresh DRAFT."""
        uid = str(salary_in.user_id)
        existing = await SalarySlip.find_one(
            SalarySlip.user_id == uid,
            SalarySlip.month == salary_in.month
        )
        if existing:
            await existing.delete()
        return await self.generate_salary_slip(salary_in)

    async def update_draft_slip(self, slip_id: str, salary_in: SalarySlipGenerate) -> dict:
        """Recalculate and update an existing DRAFT salary slip."""
        slip = await SalarySlip.get(slip_id)
        if not slip:
            raise HTTPException(status_code=404, detail="Salary slip not found")
        if slip.status != "DRAFT":
            raise HTTPException(status_code=400, detail="Only DRAFT slips can be updated")

        user = await User.find_one(User.id == int(slip.user_id)) if slip.user_id and str(slip.user_id).isdigit() else None
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        year, month_num = map(int, slip.month.split('-'))
        approved_leaves, total_leave_days, paid_leaves, unpaid_leaves = \
            await self._get_leave_data(slip.user_id, year, month_num)

        incentive_amount, slab_bonus = await self._get_incentive_data(slip.user_id, slip.month)
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
        slip.generated_at = datetime.now(UTC)
        await slip.save()
        return await self._format_slip(slip)

    async def confirm_salary_slip(self, slip_id: str, confirmed_by_id: str) -> dict:
        """Confirm a DRAFT slip, making it visible to the employee."""
        slip = await SalarySlip.get(slip_id)
        if not slip:
            raise HTTPException(status_code=404, detail="Salary slip not found")
        if slip.status != "DRAFT":
            raise HTTPException(status_code=400, detail="Only DRAFT slips can be confirmed")

        slip.status = "CONFIRMED"
        slip.confirmed_by = str(confirmed_by_id)
        slip.confirmed_at = datetime.now(UTC)
        await slip.save()
        return await self._format_slip(slip)

    async def get_user_salary_slips(self, user_id: str, show_drafts: bool = True, only_visible: bool = False) -> List[dict]:
        """Get salary slips for a specific user."""
        filters = [SalarySlip.user_id == str(user_id), SalarySlip.is_deleted == False]
        if not show_drafts:
            filters.append(SalarySlip.status == "CONFIRMED")
        if only_visible:
            filters.append(SalarySlip.is_visible_to_employee == True)
        
        slips = await SalarySlip.find(*filters).sort(-SalarySlip.month).to_list()
        return [await self._format_slip(s) for s in slips]

    async def get_all_salary_slips(self) -> List[dict]:
        """Get all salary slips (admin use)."""
        slips = await SalarySlip.find(SalarySlip.is_deleted == False).sort(-SalarySlip.month).to_list()
        return [await self._format_slip(s) for s in slips]

    async def generate_invoice_html(self, slip_id: str) -> str:
        """Generate a professional printable HTML salary slip (payslip)."""
        import base64
        slip = await SalarySlip.get(slip_id)
        if not slip:
            raise HTTPException(status_code=404, detail="Salary slip not found")

        user = await User.find_one(User.id == int(slip.user_id)) if slip.user_id and str(slip.user_id).isdigit() else None

        # Embed company logo as base64 so it works in print/new-window context
        logo_data_uri = ""
        try:
            _here = os.path.abspath(__file__)
            _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_here)))))
            _logo_white_path = os.path.join(_root, "frontend", "images", "white logo.png")
            _logo_path = os.path.join(_root, "frontend", "images", "logo.png")
            _chosen = _logo_white_path if os.path.exists(_logo_white_path) else _logo_path
            if os.path.exists(_chosen):
                with open(_chosen, "rb") as _f:
                    _ext = "png" if _chosen.endswith(".png") else "jpeg"
                    logo_data_uri = f"data:image/{_ext};base64," + base64.b64encode(_f.read()).decode()
        except Exception:
            pass

        slab_bonus = slip.slab_bonus or 0.0
        incentive_amount = slip.incentive_amount or 0.0
        daily_wage = round(slip.base_salary / 30, 2)
        extra_deduction = slip.deduction_amount or 0.0
        gross_earnings = round(slip.base_salary + incentive_amount + slab_bonus, 2)
        total_deductions = round(gross_earnings - slip.final_salary, 2)
        leave_deduction = round(total_deductions - extra_deduction, 2)
        working_days = max(0, 30 - int(slip.unpaid_leaves))

        year, month_num = map(int, slip.month.split('-'))
        month_name = f"{calendar.month_name[month_num]} {year}"

        raw_date = slip.confirmed_at or slip.generated_at
        try:
            issue_date_str = raw_date.strftime("%d %B %Y")
        except Exception:
            issue_date_str = str(raw_date)

        emp_name = (user.name or user.email) if user else f"User #{slip.user_id}"
        designation = str(user.role).replace('_', ' ').title() if user else "Employee"

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
        user_id_num = user.id if user else 0
        slip_no = f"PS-{year}-{month_num:02d}-{user_id_num:04d}"

        # Read configurable company contact from DB (fall back to defaults)
        _DEFAULT_EMAIL = "hrmangukiya3494@gmail.com"
        _DEFAULT_PHONE = "8866005029"
        try:
            _email_row = await AppSetting.find_one(AppSetting.key == "payslip_email")
            _phone_row = await AppSetting.find_one(AppSetting.key == "payslip_phone")
            company_email = _email_row.value if _email_row else _DEFAULT_EMAIL
            company_phone = _phone_row.value if _phone_row else _DEFAULT_PHONE
        except Exception:
            company_email = _DEFAULT_EMAIL
            company_phone = _DEFAULT_PHONE

        user_email = user.email if user else "N/A"
        user_department = (user.department or '<span style="font-weight:normal;color:#94a3b8;font-size:11px;">n/a</span>') if user else "N/A"
        user_phone = (user.phone or '<span style="font-weight:normal;color:#94a3b8;font-size:11px;">n/a</span>') if user else "N/A"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{slip_no} &mdash; {emp_name} &mdash; {month_name}</title>
    <style>
        @page {{ size: A4; margin: 10mm 12mm; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Arial, Helvetica, sans-serif;
            background: #dde3ec;
            color: #1a1a1a;
            font-size: 12px;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
        .a4-page {{
            width: 210mm;
            min-height: 297mm;
            background: #ffffff;
            margin: 20px auto;
            padding: 12mm 14mm 10mm;
            box-shadow: 0 6px 32px rgba(0,0,0,0.28);
        }}
        .top-banner {{
            background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
            margin: -12mm -14mm 0;
            padding: 14px 14mm;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}
        .banner-left {{ display: flex; align-items: center; gap: 14px; }}
        .logo-img {{
            height: 80px; width: auto;
            object-fit: contain;
            flex-shrink: 0;
        }}
        .company-name {{ font-size: 16px; font-weight: 800; color: #fff; line-height: 1.2; }}
        .company-sub {{ font-size: 10px; color: rgba(255,255,255,0.75); margin-top: 2px; letter-spacing: 0.4px; }}
        .banner-right {{ text-align: right; }}
        .payslip-badge {{
            font-size: 22px; font-weight: 900; color: #fff;
            letter-spacing: 2px; text-transform: uppercase;
            opacity: 0.92;
        }}
        .payslip-period {{ font-size: 11px; color: rgba(255,255,255,0.75); margin-top: 3px; text-align: right; }}
        .meta-strip {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            border: 1.5px solid #e2e8f0;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 14px;
        }}
        .meta-cell {{ padding: 10px 14px; border-right: 1px solid #e2e8f0; background: #f8fafc; }}
        .meta-cell:last-child {{ border-right: none; }}
        .meta-lbl {{ font-size: 9.5px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.7px; font-weight: 700; margin-bottom: 4px; }}
        .meta-val {{ font-size: 13px; font-weight: 800; color: #1e293b; word-break: break-word; }}
        .s-confirmed {{ color: #059669; }}
        .s-draft {{ color: #D97706; }}
        .section-box {{ border: 1.5px solid #e2e8f0; border-radius: 8px; overflow: hidden; margin-bottom: 14px; }}
        .section-hdr {{
            background: #1e3a5f; color: #fff;
            padding: 8px 14px; font-size: 10.5px;
            font-weight: 800; letter-spacing: 1.2px; text-transform: uppercase;
        }}
        .emp-grid {{ display: grid; grid-template-columns: 1fr 1fr; }}
        .emp-col:first-child {{ border-right: 1px solid #e2e8f0; }}
        .emp-row {{
            display: flex; justify-content: space-between; align-items: flex-start;
            padding: 8px 14px; border-bottom: 1px solid #f1f5f9; font-size: 12px;
        }}
        .emp-row:last-child {{ border-bottom: none; }}
        .e-lbl {{ color: #64748b; font-weight: 500; white-space: nowrap; margin-right: 8px; }}
        .e-val {{ font-weight: 700; color: #1e293b; text-align: right; word-break: break-word; max-width: 58%; }}
        .att-strip {{
            display: grid; grid-template-columns: repeat(4, 1fr);
            background: #f0f7ff; border: 1.5px solid #bfdbfe;
            border-radius: 8px; overflow: hidden; margin-bottom: 14px;
        }}
        .att-cell {{
            padding: 10px 12px; text-align: center;
            border-right: 1px solid #bfdbfe;
        }}
        .att-cell:last-child {{ border-right: none; }}
        .att-num {{ font-size: 20px; font-weight: 900; color: #1e40af; line-height: 1; }}
        .att-num.green {{ color: #059669; }}
        .att-num.red {{ color: #dc2626; }}
        .att-lbl {{ font-size: 9.5px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; font-weight: 600; }}
        .pay-table-wrap {{ display: grid; grid-template-columns: 1fr 1fr; }}
        .pay-col:first-child {{ border-right: 1px solid #e2e8f0; }}
        .pay-col-hdr {{
            background: #f8fafc; padding: 8px 14px;
            font-size: 10px; color: #64748b; font-weight: 700;
            letter-spacing: 0.7px; text-transform: uppercase;
            border-bottom: 1.5px solid #e2e8f0;
            display: flex; justify-content: space-between;
        }}
        .pay-row {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 8px 14px; border-bottom: 1px solid #f1f5f9; font-size: 12px;
        }}
        .pay-row:last-child {{ border-bottom: none; }}
        .pay-desc {{ color: #374151; }}
        .pay-desc small {{ display: block; font-size: 10px; color: #94a3b8; margin-top: 1px; }}
        .pay-amt {{ font-weight: 700; color: #1e293b; white-space: nowrap; }}
        .pay-amt.earn {{ color: #059669; }}
        .pay-amt.ded {{ color: #dc2626; }}
        .totals-row {{
            display: grid; grid-template-columns: 1fr 1fr;
            border-top: 2px solid #e2e8f0; background: #f8fafc;
        }}
        .tot-cell {{
            padding: 9px 14px; display: flex; justify-content: space-between; align-items: center;
            font-size: 12px; font-weight: 700;
        }}
        .tot-cell:first-child {{ border-right: 1px solid #e2e8f0; }}
        .tot-lbl {{ color: #374151; }}
        .tot-val.earn {{ color: #059669; }}
        .tot-val.ded {{ color: #dc2626; }}
        .net-bar {{
            background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
            color: #fff; border-radius: 8px; padding: 14px 18px;
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 16px;
        }}
        .net-words-lbl {{ font-size: 9.5px; text-transform: uppercase; letter-spacing: 0.8px; opacity: 0.75; margin-bottom: 4px; }}
        .net-words {{ font-size: 11.5px; font-style: italic; max-width: 310px; line-height: 1.4; }}
        .net-amt-lbl {{ font-size: 9.5px; text-transform: uppercase; letter-spacing: 0.8px; opacity: 0.75; margin-bottom: 2px; text-align: right; }}
        .net-amt {{ font-size: 28px; font-weight: 900; text-align: right; letter-spacing: -0.5px; }}
        .sig-section {{
            display: grid; grid-template-columns: repeat(3, 1fr);
            gap: 20px; margin-bottom: 14px;
        }}
        .sig-block {{ text-align: center; }}
        .sig-line {{
            border-top: 1px dashed #999;
            margin-top: 36px; padding-top: 5px;
            font-size: 10.5px; color: #64748b; font-weight: 600;
        }}
        .slip-footer {{
            text-align: center; font-size: 9.5px; color: #94a3b8;
            border-top: 1px solid #e2e8f0; padding-top: 10px;
            line-height: 1.6;
        }}
        .print-bar {{
            width: 210mm; margin: 14px auto;
            display: flex; gap: 10px; justify-content: center;
        }}
        .btn-print {{
            padding: 10px 32px; background: #2563eb; color: #fff;
            border: none; font-size: 13px; font-weight: 700;
            cursor: pointer; font-family: inherit; border-radius: 7px;
            letter-spacing: 0.3px;
        }}
        .btn-close-w {{
            padding: 10px 28px; background: #fff; color: #2563eb;
            border: 2px solid #2563eb; font-size: 13px; font-weight: 700;
            cursor: pointer; font-family: inherit; border-radius: 7px;
        }}
        @media print {{
            body {{ background: #fff; }}
            .a4-page {{ margin: 0; padding: 0; box-shadow: none; width: 100%; min-height: auto; }}
            .top-banner {{ margin: 0; padding: 14px 14mm; }}
            .print-bar {{ display: none; }}
        }}
    </style>
</head>
<body>

<div class="a4-page">

    <!-- TOP BANNER -->
    <div class="top-banner">
        <div class="banner-left">
            {'<img class="logo-img" src="' + logo_data_uri + '" alt="Company Logo">' if logo_data_uri else '<div style="width:52px;height:52px;background:rgba(255,255,255,0.18);border:2px solid rgba(255,255,255,0.35);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:900;color:#fff;">&#9670;</div>'}
        </div>
        <div class="banner-right">
            <div class="payslip-badge">Salary Slip</div>
            <div class="payslip-period">{month_name}</div>
            <div class="company-sub" style="margin-top:5px;">{company_email} &nbsp;&middot;&nbsp; {company_phone}</div>
        </div>
    </div>

    <!-- SLIP META STRIP -->
    <div class="meta-strip">
        <div class="meta-cell">
            <div class="meta-lbl">Slip No.</div>
            <div class="meta-val">{slip_no}</div>
        </div>
        <div class="meta-cell">
            <div class="meta-lbl">Issue Date</div>
            <div class="meta-val">{issue_date_str}</div>
        </div>
        <div class="meta-cell">
            <div class="meta-lbl">Status</div>
            <div class="meta-val {'s-confirmed' if status_str == 'CONFIRMED' else 's-draft'}">{'&#10003; Paid' if status_str == 'CONFIRMED' else '&#9679; Draft'}</div>
        </div>
        <div class="meta-cell">
            <div class="meta-lbl">Net Payable</div>
            <div class="meta-val" style="color:#2563eb;">&#8377;&nbsp;{slip.final_salary:,.2f}</div>
        </div>
    </div>

    <!-- EMPLOYEE DETAILS -->
    <div class="section-box">
        <div class="section-hdr">Employee Details</div>
        <div class="emp-grid">
            <div class="emp-col">
                <div class="emp-row">
                    <span class="e-lbl">Name</span>
                    <span class="e-val">{emp_name}</span>
                </div>
                <div class="emp-row">
                    <span class="e-lbl">Designation</span>
                    <span class="e-val">{designation}</span>
                </div>
                <div class="emp-row">
                    <span class="e-lbl">Email</span>
                    <span class="e-val">{user_email}</span>
                </div>
            </div>
            <div class="emp-col">
                <div class="emp-row">
                    <span class="e-lbl">Employee ID</span>
                    <span class="e-val">EMP-{user_id_num:04d}</span>
                </div>
                <div class="emp-row">
                    <span class="e-lbl">Department</span>
                    <span class="e-val">{user_department}</span>
                </div>
                <div class="emp-row">
                    <span class="e-lbl">Phone</span>
                    <span class="e-val">{user_phone}</span>
                </div>
            </div>
        </div>
    </div>

    <!-- ATTENDANCE SUMMARY -->
    <div class="att-strip">
        <div class="att-cell">
            <div class="att-num">30</div>
            <div class="att-lbl">Total Days</div>
        </div>
        <div class="att-cell">
            <div class="att-num">{working_days}</div>
            <div class="att-lbl">Working Days</div>
        </div>
        <div class="att-cell">
            <div class="att-num green">{slip.paid_leaves}</div>
            <div class="att-lbl">Paid Leaves</div>
        </div>
        <div class="att-cell">
            <div class="att-num red">{slip.unpaid_leaves}</div>
            <div class="att-lbl">Unpaid Leaves</div>
        </div>
    </div>

    <!-- EARNINGS & DEDUCTIONS -->
    <div class="section-box">
        <div class="section-hdr">Earnings &amp; Deductions</div>
        <div class="pay-table-wrap">
            <div class="pay-col">
                <div class="pay-col-hdr">
                    <span>Earnings</span><span>Amount (&#8377;)</span>
                </div>
                <div class="pay-row">
                    <div class="pay-desc">Basic Salary</div>
                    <div class="pay-amt earn">&#8377;&nbsp;{slip.base_salary:,.2f}</div>
                </div>
                <div class="pay-row">
                    <div class="pay-desc">Performance Incentive</div>
                    <div class="pay-amt earn">&#8377;&nbsp;{incentive_amount:,.2f}</div>
                </div>
                <div class="pay-row">
                    <div class="pay-desc">Slab Bonus</div>
                    <div class="pay-amt earn">&#8377;&nbsp;{slab_bonus:,.2f}</div>
                </div>
            </div>
            <div class="pay-col">
                <div class="pay-col-hdr">
                    <span>Deductions</span><span>Amount (&#8377;)</span>
                </div>
                <div class="pay-row">
                    <div class="pay-desc">
                        Leave Deduction
                        <small>{slip.unpaid_leaves} unpaid day(s) &times; &#8377;{daily_wage:,.2f}/day</small>
                    </div>
                    <div class="pay-amt ded">&#8377;&nbsp;{leave_deduction:,.2f}</div>
                </div>
                <div class="pay-row">
                    <div class="pay-desc">Other Deductions</div>
                    <div class="pay-amt ded">&#8377;&nbsp;{extra_deduction:,.2f}</div>
                </div>
            </div>
        </div>
        <div class="totals-row">
            <div class="tot-cell">
                <span class="tot-lbl">Total Earnings</span>
                <span class="tot-val earn">&#8377;&nbsp;{gross_earnings:,.2f}</span>
            </div>
            <div class="tot-cell">
                <span class="tot-lbl">Total Deductions</span>
                <span class="tot-val ded">&#8377;&nbsp;{total_deductions:,.2f}</span>
            </div>
        </div>
    </div>

    <!-- NET PAY -->
    <div class="net-bar">
        <div>
            <div class="net-words-lbl">Net Salary in Words</div>
            <div class="net-words">{net_in_words}</div>
        </div>
        <div>
            <div class="net-amt-lbl">Net Amount Payable</div>
            <div class="net-amt">&#8377;&nbsp;{slip.final_salary:,.2f}</div>
        </div>
    </div>

    <!-- SIGNATURE SECTION -->
    <div class="sig-section">
        <div class="sig-block">
            <div class="sig-line">Employee Signature</div>
        </div>
        <div class="sig-block">
            <div class="sig-line">HR / Accounts</div>
        </div>
        <div class="sig-block">
            <div class="sig-line">Authorized Signatory</div>
        </div>
    </div>

    <!-- FOOTER -->
    <div class="slip-footer">
        This is a computer generated salary slip by HK DigiVerse LLP &mdash; Confidential &mdash; For Employee Use Only
    </div>

</div>

<div class="print-bar">
    <button class="btn-close-w" onclick="window.close()">&#10005;&nbsp; Close</button>
    <button class="btn-print" onclick="window.print()">&#128438;&nbsp; Print / Save as PDF</button>
</div>

</body>
</html>"""
        return html
