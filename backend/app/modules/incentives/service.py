# backend/app/modules/incentives/service.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from fastapi import HTTPException
from datetime import datetime, UTC, timedelta
from typing import List, Optional

from app.modules.incentives.models import (
    IncentiveSlab, IncentiveSlip
)
from app.modules.incentives.schemas import IncentiveCalculationRequest, IncentiveSlipRead
from app.modules.users.models import User, UserRole
from app.modules.clients.models import Client

class IncentiveService:
    def __init__(self, db: Session):
        self.db = db

    def _ensure_slab_bonus_column(self) -> None:
        """Self-heal for environments where incentive slip migrations weren't applied yet."""
        try:
            self.db.execute(
                text("ALTER TABLE incentive_slips ADD COLUMN IF NOT EXISTS slab_bonus_amount DOUBLE PRECISION DEFAULT 0")
            )
            self.db.execute(
                text("ALTER TABLE incentive_slips ADD COLUMN IF NOT EXISTS is_visible_to_employee BOOLEAN DEFAULT false")
            )
            self.db.execute(
                text("ALTER TABLE incentive_slips ADD COLUMN IF NOT EXISTS employee_remarks TEXT")
            )
            self.db.execute(
                text("ALTER TABLE incentive_slips ADD COLUMN IF NOT EXISTS manager_remarks TEXT")
            )
            self.db.commit()
        except Exception:
            self.db.rollback()

    @staticmethod
    def _user_display_name(user: Optional[User], user_id: int) -> str:
        if not user:
            return f"Employee #{user_id}"
        return user.name or f"Employee #{user_id}"

    @staticmethod
    def _get_period_bounds(period: str) -> tuple[datetime, datetime]:
        year, month = map(int, period.split('-'))
        period_start = datetime(year, month, 1, tzinfo=UTC)
        if month == 12:
            next_month_start = datetime(year + 1, 1, 1, tzinfo=UTC)
        else:
            next_month_start = datetime(year, month + 1, 1, tzinfo=UTC)
        return period_start, next_month_start

    def _apply_role_scope(self, query, user: User):
        if user.role == UserRole.TELESALES or user.role == UserRole.SALES:
            return query.filter(Client.owner_id == user.id)
        if user.role == UserRole.PROJECT_MANAGER:
            return query.filter(Client.pm_id == user.id)
        if user.role == UserRole.PROJECT_MANAGER_AND_SALES:
            from sqlalchemy import or_
            return query.filter(or_(Client.owner_id == user.id, Client.pm_id == user.id))
        return query.filter(Client.id == -1)

    def _select_applied_slab(self, achieved: int) -> Optional[IncentiveSlab]:
        """Select one slab deterministically for a given achieved count."""
        if achieved <= 0:
            return None

        # Primary: slab whose range includes achieved. If overlaps exist, prefer the tightest upper band.
        applied_slab = self.db.query(IncentiveSlab).filter(
            IncentiveSlab.min_units <= achieved,
            IncentiveSlab.max_units >= achieved
        ).order_by(IncentiveSlab.min_units.desc(), IncentiveSlab.max_units.asc()).first()

        if applied_slab:
            return applied_slab

        # Fallback: use nearest lower slab instead of an arbitrary highest slab.
        return self.db.query(IncentiveSlab).filter(
            IncentiveSlab.max_units <= achieved
        ).order_by(IncentiveSlab.max_units.desc(), IncentiveSlab.min_units.desc()).first()

    def calculate_incentive(self, calc_in: IncentiveCalculationRequest):
        self._ensure_slab_bonus_column()
        user = self.db.query(User).filter(User.id == calc_in.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not getattr(user, "incentive_enabled", True):
            raise HTTPException(status_code=400, detail="Incentive is disabled for this user")

        force_recalculate = bool(getattr(calc_in, "force_recalculate", False))

        existing_slips = self.db.query(IncentiveSlip).filter(
            IncentiveSlip.user_id == calc_in.user_id,
            IncentiveSlip.period == calc_in.period
        ).order_by(IncentiveSlip.generated_at.desc(), IncentiveSlip.id.desc()).all()
        existing_slip = existing_slips[0] if existing_slips else None

        # Keep one canonical slip per user+period when recalculating in legacy duplicated data.
        if force_recalculate and len(existing_slips) > 1:
            for duplicate_slip in existing_slips[1:]:
                self.db.delete(duplicate_slip)

        if existing_slip and not force_recalculate:
            raise HTTPException(status_code=400, detail="Incentive slip for this period already exists")

        # Incentive logic is slab-based only; target is no longer used.
        target = 0

        if calc_in.closed_units is not None:
            achieved = calc_in.closed_units
        else:
            # Period is based on 10-day eligibility date, not client creation month.
            period_start, next_month_start = self._get_period_bounds(calc_in.period)
            
            # 10-day break period: Client must be created before (now - 10 days) to be eligible for payout.
            # 7-day refund policy: If client is deactivated (refunded) within 7 days (or any time), they are excluded.
            # In practice, since we only count clients who are at least 10 days old AND currently active,
            # anything refunded within 7 days is automatically excluded.
            
            eligibility_start = period_start - timedelta(days=10)
            eligibility_end = next_month_start - timedelta(days=10)
            ten_days_ago = datetime.now(UTC) - timedelta(days=10)

            query = self.db.query(Client).filter(
                Client.is_active == True,
                Client.is_deleted == False,
                Client.created_at >= eligibility_start,
                Client.created_at < eligibility_end,
                Client.created_at <= ten_days_ago
            )
            achieved = self._apply_role_scope(query, user).count()

        percentage = 0

        # Find slab based on achieved units.
        applied_slab = self._select_applied_slab(achieved)

        incentive_per_unit: float = 0.0
        slab_bonus: float = 0.0
        total_incentive: float = 0.0

        if applied_slab:
            incentive_per_unit = applied_slab.incentive_per_unit
            # Milestone bonus: pay slab bonus only when slab max is reached.
            slab_bonus = applied_slab.slab_bonus if achieved >= applied_slab.max_units else 0.0
            total_incentive = (achieved * incentive_per_unit) + slab_bonus
            applied_slab_label = f"{applied_slab.min_units}-{applied_slab.max_units}"
        else:
            applied_slab_label = None

        if existing_slip and force_recalculate:
            existing_slip.target = target
            existing_slip.achieved = achieved
            existing_slip.percentage = round(percentage, 2)
            existing_slip.applied_slab = applied_slab_label
            existing_slip.amount_per_unit = incentive_per_unit
            existing_slip.slab_bonus_amount = slab_bonus
            existing_slip.total_incentive = round(total_incentive, 2)
            existing_slip.is_visible_to_employee = True
            existing_slip.generated_at = datetime.now(UTC)
            db_slip = existing_slip
        else:
            db_slip = IncentiveSlip(
                user_id=calc_in.user_id,
                period=calc_in.period,
                target=target,
                achieved=achieved,
                percentage=round(percentage, 2),
                applied_slab=applied_slab_label,
                amount_per_unit=incentive_per_unit,
                slab_bonus_amount=slab_bonus,
                is_visible_to_employee=True,
                total_incentive=round(total_incentive, 2),
                generated_at=datetime.now(UTC)
            )
            self.db.add(db_slip)

        self.db.commit()
        self.db.refresh(db_slip)

        res = IncentiveSlipRead.model_validate(db_slip)
        res.user_name = self._user_display_name(user, user.id)
        return res

    def calculate_incentive_bulk(self, period: str) -> dict:
        """Calculate incentives for all incentive-enabled non-admin users for a period."""
        users = self.db.query(User).filter(
            User.is_active == True,
            User.is_deleted == False,
            User.role != UserRole.ADMIN,
            User.role != UserRole.CLIENT
        ).order_by(User.id.asc()).all()

        processed_users = 0
        created_slips = 0
        skipped_existing = 0
        skipped_disabled = 0
        failed_users = 0
        failures: list[dict] = []

        for user in users:
            processed_users += 1

            if not getattr(user, "incentive_enabled", True):
                skipped_disabled += 1
                continue

            existing_slip = self.db.query(IncentiveSlip).filter(
                IncentiveSlip.user_id == user.id,
                IncentiveSlip.period == period
            ).first()
            if existing_slip:
                skipped_existing += 1
                continue

            try:
                self.calculate_incentive(IncentiveCalculationRequest(user_id=user.id, period=period))
                created_slips += 1
            except HTTPException as exc:
                failed_users += 1
                failures.append({
                    "user_id": user.id,
                    "user_name": self._user_display_name(user, user.id),
                    "error": str(exc.detail),
                })
            except Exception as exc:
                failed_users += 1
                failures.append({
                    "user_id": user.id,
                    "user_name": self._user_display_name(user, user.id),
                    "error": str(exc),
                })

        return {
            "period": period,
            "processed_users": processed_users,
            "created_slips": created_slips,
            "skipped_existing": skipped_existing,
            "skipped_disabled": skipped_disabled,
            "failed_users": failed_users,
            "failures": failures,
        }

    def preview_incentive(self, user_id: int, period: str, closed_units: Optional[int] = None) -> dict:
        """Calculate incentive breakdown without saving. Returns preview data."""
        self._ensure_slab_bonus_column()

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not getattr(user, "incentive_enabled", True):
            raise HTTPException(status_code=400, detail="Incentive is disabled for this user")

        target = 0
        period_start, next_month_start = self._get_period_bounds(period)
        eligibility_start = period_start - timedelta(days=10)
        eligibility_end = next_month_start - timedelta(days=10)
        ten_days_ago = datetime.now(UTC) - timedelta(days=10)

        base_query = self.db.query(Client).filter(
            Client.is_deleted == False,
            Client.created_at >= eligibility_start,
            Client.created_at < eligibility_end
        )
        base_query = self._apply_role_scope(base_query, user)

        total_tasks = base_query.count()
        confirmed_tasks = base_query.filter(
            Client.is_active == True,
            Client.created_at <= ten_days_ago
        ).count() if closed_units is None else closed_units
        pending_tasks = base_query.filter(
            Client.is_active == True,
            Client.created_at > ten_days_ago
        ).count()
        refunded_tasks = base_query.filter(Client.is_active == False).count()

        achieved = confirmed_tasks
        percentage = 0.0

        applied_slab = self._select_applied_slab(achieved)

        incentive_per_task = applied_slab.incentive_per_unit if applied_slab else 0.0
        slab_bonus = (applied_slab.slab_bonus if achieved >= applied_slab.max_units else 0.0) if applied_slab else 0.0
        slab_range = f"{applied_slab.min_units}-{applied_slab.max_units}" if applied_slab else None
        base_incentive = achieved * incentive_per_task
        total_incentive = base_incentive + slab_bonus

        slip_exists = self.db.query(IncentiveSlip).filter(
            IncentiveSlip.user_id == user_id,
            IncentiveSlip.period == period
        ).first() is not None

        return {
            "user_id": user_id,
            "user_name": self._user_display_name(user, user_id),
            "period": period,
            "target": target,
            "confirmed_tasks": achieved,
            "pending_tasks": pending_tasks,
            "refunded_tasks": refunded_tasks,
            "total_tasks_in_period": total_tasks,
            "slab_range": slab_range,
            "incentive_per_task": incentive_per_task,
            "base_incentive": round(base_incentive, 2),
            "slab_bonus": round(slab_bonus, 2),
            "total_incentive": round(total_incentive, 2),
            "percentage": round(percentage, 2),
            "slip_exists": slip_exists,
        }

    @staticmethod
    def _to_int(value, default: int = 0) -> int:
        try:
            return int(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_float(value, default: float = 0.0) -> float:
        try:
            return float(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    def _get_slip_rows_fallback(self, user_id: Optional[int] = None) -> list[dict]:
        where_clause = "WHERE s.user_id = :user_id" if user_id is not None else ""
        params = {"user_id": user_id} if user_id is not None else {}
        stmt = text(f"""
            SELECT
                s.id,
                s.user_id,
                s.period,
                s.target,
                s.achieved,
                s.percentage,
                s.applied_slab,
                s.amount_per_unit,
                s.slab_bonus_amount,
                s.is_visible_to_employee,
                s.employee_remarks,
                s.manager_remarks,
                s.total_incentive,
                s.generated_at,
                u.name AS user_name
            FROM incentive_slips s
            LEFT JOIN users u ON u.id = s.user_id
            {where_clause}
            ORDER BY s.period DESC, s.generated_at DESC, s.id DESC
        """)
        rows = self.db.execute(stmt, params).mappings().all()
        return [dict(r) for r in rows]

    def _serialize_slip_rows(self, rows: list[dict]) -> list[IncentiveSlipRead]:
        results: list[IncentiveSlipRead] = []
        for row in rows:
            slip = IncentiveSlipRead(
                id=self._to_int(row.get("id")),
                user_id=self._to_int(row.get("user_id")),
                period=str(row.get("period") or ""),
                target=self._to_int(row.get("target")),
                achieved=self._to_int(row.get("achieved")),
                percentage=self._to_float(row.get("percentage")),
                applied_slab=(str(row.get("applied_slab")) if row.get("applied_slab") is not None else None),
                amount_per_unit=self._to_float(row.get("amount_per_unit")),
                slab_bonus_amount=self._to_float(row.get("slab_bonus_amount")),
                is_visible_to_employee=bool(row.get("is_visible_to_employee")),
                employee_remarks=row.get("employee_remarks"),
                manager_remarks=row.get("manager_remarks"),
                total_incentive=self._to_float(row.get("total_incentive")),
                generated_at=row.get("generated_at"),
                user_name=row.get("user_name") or f"Employee #{self._to_int(row.get('user_id'))}",
            )
            results.append(slip)
        return results

    def get_user_incentive_slips(self, user_id: int):
        self._ensure_slab_bonus_column()
        try:
            slips = self.db.query(IncentiveSlip).options(
                joinedload(IncentiveSlip.user)
            ).filter(
                IncentiveSlip.user_id == user_id
            ).order_by(IncentiveSlip.period.desc()).all()
            results = []
            for s in slips:
                r = IncentiveSlipRead.model_validate(s)
                r.user_name = self._user_display_name(s.user, s.user_id)
                results.append(r)
            return results
        except (ProgrammingError, OperationalError) as e:
            self.db.rollback()
            try:
                return self._serialize_slip_rows(self._get_slip_rows_fallback(user_id=user_id))
            except Exception:
                return []

    def get_visible_user_incentive_slips(self, user_id: int):
        self._ensure_slab_bonus_column()
        try:
            slips = self.db.query(IncentiveSlip).options(
                joinedload(IncentiveSlip.user)
            ).filter(
                IncentiveSlip.user_id == user_id,
                IncentiveSlip.is_visible_to_employee == True
            ).order_by(IncentiveSlip.period.desc()).all()
            results = []
            for s in slips:
                r = IncentiveSlipRead.model_validate(s)
                r.user_name = self._user_display_name(s.user, s.user_id)
                results.append(r)
            return results
        except Exception:
            self.db.rollback()
            try:
                rows = [r for r in self._get_slip_rows_fallback(user_id=user_id) if bool(r.get("is_visible_to_employee"))]
                return self._serialize_slip_rows(rows)
            except Exception:
                return []

    def get_all_incentive_slips(self):
        self._ensure_slab_bonus_column()
        try:
            slips = self.db.query(IncentiveSlip).options(
                joinedload(IncentiveSlip.user)
            ).order_by(IncentiveSlip.period.desc()).all()
            results = []
            for s in slips:
                r = IncentiveSlipRead.model_validate(s)
                r.user_name = self._user_display_name(s.user, s.user_id)
                results.append(r)
            return results
        except (ProgrammingError, OperationalError) as e:
            self.db.rollback()
            try:
                return self._serialize_slip_rows(self._get_slip_rows_fallback())
            except Exception:
                return []
        except Exception:
            self.db.rollback()
            try:
                return self._serialize_slip_rows(self._get_slip_rows_fallback())
            except Exception:
                return []

