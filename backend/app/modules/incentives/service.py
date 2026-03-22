from fastapi import HTTPException
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from app.modules.incentives.models import IncentiveSlab, IncentiveSlip
from app.modules.incentives.schemas import IncentiveCalculationRequest, IncentiveSlipRead
from app.modules.users.models import User, UserRole
from app.modules.clients.models import Client

class IncentiveService:

    @staticmethod
    def _user_display_name(user: Optional[User], user_id: str) -> str:
        if not user:
            return f"Employee #{user_id}"
        return user.name or f"Employee #{user_id}"

    @staticmethod
    def _get_period_bounds(period: str) -> tuple:
        year, month = map(int, period.split('-'))
        period_start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            next_month_start = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month_start = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        return period_start, next_month_start

    async def _select_applied_slab(self, achieved: int) -> Optional[IncentiveSlab]:
        if achieved <= 0:
            return None
        slabs = await IncentiveSlab.find(IncentiveSlab.min_units <= achieved, IncentiveSlab.max_units >= achieved).to_list()
        if slabs:
            return sorted(slabs, key=lambda s: (-s.min_units, s.max_units))[0]
        fallback_slabs = await IncentiveSlab.find(IncentiveSlab.max_units <= achieved).to_list()
        if fallback_slabs:
            return sorted(fallback_slabs, key=lambda s: (-s.max_units, -s.min_units))[0]
        return None

    async def _get_achieved_count(self, user: User, period: str, closed_units: Optional[int] = None) -> int:
        if closed_units is not None:
            return closed_units
        period_start, next_month_start = self._get_period_bounds(period)
        eligibility_start = period_start - timedelta(days=10)
        eligibility_end = next_month_start - timedelta(days=10)
        ten_days_ago = datetime.now(timezone.utc) - timedelta(days=10)
        query_filter = [Client.is_active == True, Client.created_at >= eligibility_start, Client.created_at < eligibility_end, Client.created_at <= ten_days_ago]
        if user.role in [UserRole.TELESALES, UserRole.SALES]:
            query_filter.append(Client.owner_id == user.id)
        elif user.role == UserRole.PROJECT_MANAGER:
            query_filter.append(Client.pm_id == user.id)
        elif user.role == UserRole.PROJECT_MANAGER_AND_SALES:
            clients = await Client.find(*query_filter).to_list()
            return len([c for c in clients if c.owner_id == user.id or c.pm_id == user.id])
        else:
            return 0
        return await Client.find(*query_filter).count()

    async def calculate_incentive(self, calc_in: IncentiveCalculationRequest):
        user = await User.find_one(User.id == calc_in.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not getattr(user, "incentive_enabled", True):
            raise HTTPException(status_code=400, detail="Incentive is disabled for this user")
        force_recalculate = bool(getattr(calc_in, "force_recalculate", False))
        existing_slips = await IncentiveSlip.find(IncentiveSlip.user_id == calc_in.user_id, IncentiveSlip.period == calc_in.period).sort(-IncentiveSlip.generated_at).to_list()
        existing_slip = existing_slips[0] if existing_slips else None
        if force_recalculate and len(existing_slips) > 1:
            for duplicate_slip in existing_slips[1:]:
                await duplicate_slip.delete()
        if existing_slip and not force_recalculate:
            raise HTTPException(status_code=400, detail="Incentive slip for this period already exists")
        achieved = await self._get_achieved_count(user, calc_in.period, calc_in.closed_units)
        applied_slab = await self._select_applied_slab(achieved)
        incentive_per_unit = applied_slab.incentive_per_unit if applied_slab else 0.0
        slab_bonus = (applied_slab.slab_bonus if applied_slab and achieved >= applied_slab.max_units else 0.0)
        total_incentive = (achieved * incentive_per_unit) + slab_bonus
        applied_slab_label = f"{applied_slab.min_units}-{applied_slab.max_units}" if applied_slab else None
        if existing_slip and force_recalculate:
            existing_slip.target = 0
            existing_slip.achieved = achieved
            existing_slip.percentage = 0.0
            existing_slip.applied_slab = applied_slab_label
            existing_slip.amount_per_unit = incentive_per_unit
            existing_slip.slab_bonus_amount = slab_bonus
            existing_slip.total_incentive = round(total_incentive, 2)
            existing_slip.generated_at = datetime.now(timezone.utc)
            await existing_slip.save()
            db_slip = existing_slip
        else:
            db_slip = IncentiveSlip(user_id=calc_in.user_id, period=calc_in.period, target=0, achieved=achieved, percentage=0.0, applied_slab=applied_slab_label, amount_per_unit=incentive_per_unit, slab_bonus_amount=slab_bonus, is_visible_to_employee=False, total_incentive=round(total_incentive, 2), generated_at=datetime.now(timezone.utc))
            await db_slip.insert()
        res = IncentiveSlipRead.model_validate(db_slip.model_dump())
        res.user_name = self._user_display_name(user, user.id)
        return res

    async def calculate_incentive_bulk(self, period: str) -> dict:
        users = await User.find(User.is_active == True, User.is_deleted != True, User.role != UserRole.ADMIN, User.role != UserRole.CLIENT).to_list()
        processed_users = created_slips = skipped_existing = skipped_disabled = failed_users = 0
        failures = []
        for user in users:
            processed_users += 1
            if not getattr(user, "incentive_enabled", True):
                skipped_disabled += 1
                continue
            existing_slip = await IncentiveSlip.find_one(IncentiveSlip.user_id == user.id, IncentiveSlip.period == period)
            if existing_slip:
                skipped_existing += 1
                continue
            try:
                await self.calculate_incentive(IncentiveCalculationRequest(user_id=user.id, period=period))
                created_slips += 1
            except Exception as exc:
                failed_users += 1
                failures.append({"user_id": user.id, "user_name": self._user_display_name(user, user.id), "error": str(exc)})
        return {"period": period, "processed_users": processed_users, "created_slips": created_slips, "skipped_existing": skipped_existing, "skipped_disabled": skipped_disabled, "failed_users": failed_users, "failures": failures}

    async def preview_incentive(self, user_id: str, period: str, closed_units: Optional[int] = None) -> dict:
        user = await User.find_one(User.id == user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not getattr(user, "incentive_enabled", True):
            raise HTTPException(status_code=400, detail="Incentive is disabled for this user")
        period_start, next_month_start = self._get_period_bounds(period)
        eligibility_start = period_start - timedelta(days=10)
        eligibility_end = next_month_start - timedelta(days=10)
        ten_days_ago = datetime.now(timezone.utc) - timedelta(days=10)
        base_clients = await Client.find(Client.created_at >= eligibility_start, Client.created_at < eligibility_end).to_list()
        if user.role in [UserRole.TELESALES, UserRole.SALES]:
            base_clients = [c for c in base_clients if c.owner_id == user_id]
        elif user.role == UserRole.PROJECT_MANAGER:
            base_clients = [c for c in base_clients if c.pm_id == user_id]
        elif user.role == UserRole.PROJECT_MANAGER_AND_SALES:
            base_clients = [c for c in base_clients if c.owner_id == user_id or c.pm_id == user_id]
        else:
            base_clients = []
        total_tasks = len(base_clients)
        confirmed_tasks = closed_units if closed_units is not None else len([c for c in base_clients if c.is_active and c.created_at <= ten_days_ago])
        pending_tasks = len([c for c in base_clients if c.is_active and c.created_at > ten_days_ago])
        refunded_tasks = len([c for c in base_clients if not c.is_active])
        achieved = confirmed_tasks
        applied_slab = await self._select_applied_slab(achieved)
        incentive_per_task = applied_slab.incentive_per_unit if applied_slab else 0.0
        slab_bonus = (applied_slab.slab_bonus if applied_slab and achieved >= applied_slab.max_units else 0.0)
        slab_range = f"{applied_slab.min_units}-{applied_slab.max_units}" if applied_slab else None
        base_incentive = achieved * incentive_per_task
        total_incentive = base_incentive + slab_bonus
        slip_exists = await IncentiveSlip.find_one(IncentiveSlip.user_id == user_id, IncentiveSlip.period == period) is not None
        return {"user_id": user_id, "user_name": self._user_display_name(user, user_id), "period": period, "target": 0, "confirmed_tasks": achieved, "pending_tasks": pending_tasks, "refunded_tasks": refunded_tasks, "total_tasks_in_period": total_tasks, "slab_range": slab_range, "incentive_per_task": incentive_per_task, "base_incentive": round(base_incentive, 2), "slab_bonus": round(slab_bonus, 2), "total_incentive": round(total_incentive, 2), "percentage": 0.0, "slip_exists": slip_exists}

    async def get_user_incentive_slips(self, user_id: str):
        try:
            slips = await IncentiveSlip.find(IncentiveSlip.user_id == user_id).sort(-IncentiveSlip.period).to_list()
            results = []
            for s in slips:
                user = await User.find_one(User.id == s.user_id)
                r = IncentiveSlipRead.model_validate(s.model_dump())
                r.user_name = self._user_display_name(user, s.user_id)
                results.append(r)
            return results
        except Exception:
            return []

    async def get_visible_user_incentive_slips(self, user_id: str):
        try:
            slips = await IncentiveSlip.find(IncentiveSlip.user_id == user_id, IncentiveSlip.is_visible_to_employee == True).sort(-IncentiveSlip.period).to_list()
            results = []
            for s in slips:
                user = await User.find_one(User.id == s.user_id)
                r = IncentiveSlipRead.model_validate(s.model_dump())
                r.user_name = self._user_display_name(user, s.user_id)
                results.append(r)
            return results
        except Exception:
            return []

    async def get_all_incentive_slips(self):
        try:
            slips = await IncentiveSlip.find_all().sort(-IncentiveSlip.period).to_list()
            results = []
            for s in slips:
                user = await User.find_one(User.id == s.user_id)
                r = IncentiveSlipRead.model_validate(s.model_dump())
                r.user_name = self._user_display_name(user, s.user_id)
                results.append(r)
            return results
        except Exception:
            return []
