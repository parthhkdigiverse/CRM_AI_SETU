from sqlalchemy.orm import Session
from sqlalchemy import extract
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
        """Self-heal for environments where migration wasn't applied yet."""
        try:
            self.db.execute(
                text("ALTER TABLE incentive_slips ADD COLUMN IF NOT EXISTS slab_bonus_amount DOUBLE PRECISION DEFAULT 0")
            )
            self.db.commit()
        except Exception:
            self.db.rollback()

    @staticmethod
    def _user_display_name(user: Optional[User], user_id: int) -> str:
        if not user:
            return f"Employee #{user_id}"
        return user.name or f"Employee #{user_id}"

    def calculate_incentive(self, calc_in: IncentiveCalculationRequest):
        self._ensure_slab_bonus_column()
        user = self.db.query(User).filter(User.id == calc_in.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not getattr(user, "incentive_enabled", True):
            raise HTTPException(status_code=400, detail="Incentive is disabled for this user")

        existing_slip = self.db.query(IncentiveSlip).filter(
            IncentiveSlip.user_id == calc_in.user_id,
            IncentiveSlip.period == calc_in.period
        ).first()
        if existing_slip:
            raise HTTPException(status_code=400, detail="Incentive slip for this period already exists")

        # Incentive logic is slab-based only; target is no longer used.
        target = 0

        if calc_in.closed_units is not None:
            achieved = calc_in.closed_units
        else:
            # 10-day lock: only count clients added > 10 days ago and not refunded (is_active=True)
            ten_days_ago = datetime.now(UTC) - timedelta(days=10)
            year, month = map(int, calc_in.period.split('-'))
            query = self.db.query(Client).filter(
                extract('year', Client.created_at) == year,
                extract('month', Client.created_at) == month,
                Client.is_active == True,
                Client.created_at <= ten_days_ago
            )
            if user.role == UserRole.TELESALES or user.role == UserRole.SALES:
                achieved = query.filter(Client.owner_id == user.id).count()
            elif user.role == UserRole.PROJECT_MANAGER:
                achieved = query.filter(Client.pm_id == user.id).count()
            elif user.role == UserRole.PROJECT_MANAGER_AND_SALES:
                from sqlalchemy import or_
                achieved = query.filter(or_(Client.owner_id == user.id, Client.pm_id == user.id)).count()
            else:
                achieved = 0

        percentage = 0

        # Find Slab based on achieved units
        applied_slab = self.db.query(IncentiveSlab).filter(
            IncentiveSlab.min_units <= achieved,
            IncentiveSlab.max_units >= achieved
        ).first()

        # Fallback to highest slab if achieved exceeds all defined max_units
        if not applied_slab and achieved > 0:
            applied_slab = self.db.query(IncentiveSlab).order_by(IncentiveSlab.max_units.desc()).first()

        incentive_per_unit: float = 0.0
        slab_bonus: float = 0.0
        total_incentive: float = 0.0

        if applied_slab:
            incentive_per_unit = applied_slab.incentive_per_unit
            slab_bonus = applied_slab.slab_bonus
            total_incentive = (achieved * incentive_per_unit) + slab_bonus
            applied_slab_label = f"{applied_slab.min_units}-{applied_slab.max_units}"
        else:
            applied_slab_label = None

        db_slip = IncentiveSlip(
            user_id=calc_in.user_id,
            period=calc_in.period,
            target=target,
            achieved=achieved,
            percentage=round(percentage, 2),
            applied_slab=applied_slab_label,
            amount_per_unit=incentive_per_unit,
            slab_bonus_amount=slab_bonus,
            total_incentive=round(total_incentive, 2),
            generated_at=datetime.now(UTC)
        )
        self.db.add(db_slip)
        self.db.commit()
        self.db.refresh(db_slip)

        res = IncentiveSlipRead.model_validate(db_slip)
        res.user_name = self._user_display_name(user, user.id)
        return res

    def preview_incentive(self, user_id: int, period: str, closed_units: Optional[int] = None) -> dict:
        """Calculate incentive breakdown without saving. Returns preview data."""
        from sqlalchemy import or_
        self._ensure_slab_bonus_column()

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not getattr(user, "incentive_enabled", True):
            raise HTTPException(status_code=400, detail="Incentive is disabled for this user")

        target = 0
        ten_days_ago = datetime.now(UTC) - timedelta(days=10)
        year, month = map(int, period.split('-'))

        base_query = self.db.query(Client).filter(
            extract('year', Client.created_at) == year,
            extract('month', Client.created_at) == month
        )
        if user.role in [UserRole.TELESALES, UserRole.SALES]:
            base_query = base_query.filter(Client.owner_id == user.id)
        elif user.role == UserRole.PROJECT_MANAGER:
            base_query = base_query.filter(Client.pm_id == user.id)
        elif user.role == UserRole.PROJECT_MANAGER_AND_SALES:
            base_query = base_query.filter(or_(Client.owner_id == user.id, Client.pm_id == user.id))

        total_tasks = base_query.count()
        confirmed_tasks = base_query.filter(
            Client.is_active == True,
            Client.created_at <= ten_days_ago
        ).count() if closed_units is None else closed_units
        pending_tasks = base_query.filter(Client.created_at > ten_days_ago).count()
        refunded_tasks = base_query.filter(Client.is_active == False).count()

        achieved = confirmed_tasks
        percentage = 0.0

        applied_slab = self.db.query(IncentiveSlab).filter(
            IncentiveSlab.min_units <= achieved,
            IncentiveSlab.max_units >= achieved
        ).first()
        if not applied_slab and achieved > 0:
            applied_slab = self.db.query(IncentiveSlab).order_by(IncentiveSlab.max_units.desc()).first()

        incentive_per_task = applied_slab.incentive_per_unit if applied_slab else 0.0
        slab_bonus = applied_slab.slab_bonus if applied_slab else 0.0
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

    def get_user_incentive_slips(self, user_id: int):
        self._ensure_slab_bonus_column()
        try:
            slips = self.db.query(IncentiveSlip).filter(
                IncentiveSlip.user_id == user_id
            ).order_by(IncentiveSlip.period.desc()).all()
        except (ProgrammingError, OperationalError) as e:
            if "slab_bonus_amount" in str(e):
                self.db.rollback()
                self._ensure_slab_bonus_column()
                slips = self.db.query(IncentiveSlip).filter(
                    IncentiveSlip.user_id == user_id
                ).order_by(IncentiveSlip.period.desc()).all()
            else:
                raise
        results = []
        for s in slips:
            r = IncentiveSlipRead.model_validate(s)
            r.user_name = self._user_display_name(s.user, s.user_id)
            results.append(r)
        return results

    def get_all_incentive_slips(self):
        self._ensure_slab_bonus_column()
        try:
            slips = self.db.query(IncentiveSlip).order_by(IncentiveSlip.period.desc()).all()
        except (ProgrammingError, OperationalError) as e:
            if "slab_bonus_amount" in str(e):
                self.db.rollback()
                self._ensure_slab_bonus_column()
                slips = self.db.query(IncentiveSlip).order_by(IncentiveSlip.period.desc()).all()
            else:
                raise
        results = []
        for s in slips:
            r = IncentiveSlipRead.model_validate(s)
            r.user_name = self._user_display_name(s.user, s.user_id)
            results.append(r)
        return results

