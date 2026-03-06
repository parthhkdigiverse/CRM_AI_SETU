from sqlalchemy.orm import Session
from sqlalchemy import extract
from fastapi import HTTPException
from datetime import datetime, UTC
from typing import List, Optional

from app.modules.incentives.models import (
    IncentiveTarget, IncentiveSlab, IncentiveSlip
)
from app.modules.incentives.schemas import IncentiveCalculationRequest, IncentiveSlipRead
from app.modules.users.models import User, UserRole
from app.modules.clients.models import Client

class IncentiveService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_incentive(self, calc_in: IncentiveCalculationRequest):
        user = self.db.query(User).filter(User.id == calc_in.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        existing_slip = self.db.query(IncentiveSlip).filter(
            IncentiveSlip.user_id == calc_in.user_id,
            IncentiveSlip.period == calc_in.period
        ).first()
        if existing_slip:
            raise HTTPException(status_code=400, detail="Incentive slip for this period already exists")

        # Determine Target: use user's own target, fallback to role-based target
        target = user.target or 0
        if target == 0:
            role_target = self.db.query(IncentiveTarget).filter(
                IncentiveTarget.role == user.role,
                IncentiveTarget.period == "Monthly"
            ).first()
            if role_target:
                target = role_target.target_count

        if target == 0:
            raise HTTPException(status_code=400, detail="Target not set for user or role")

        if calc_in.closed_units is not None:
            achieved = calc_in.closed_units
        else:
            year, month = map(int, calc_in.period.split('-'))
            # Calculate achieved units based on role
            query = self.db.query(Client).filter(
                extract('year', Client.created_at) == year,
                extract('month', Client.created_at) == month
            )
            
            if user.role == UserRole.TELESALES or user.role == UserRole.SALES:
                achieved = query.filter(Client.owner_id == user.id).count()
            elif user.role == UserRole.PROJECT_MANAGER:
                achieved = query.filter(Client.pm_id == user.id).count()
            elif user.role == UserRole.PROJECT_MANAGER_AND_SALES:
                # Count if either owner OR PM
                from sqlalchemy import or_
                achieved = query.filter(or_(Client.owner_id == user.id, Client.pm_id == user.id)).count()
            else:
                achieved = 0

        percentage = (achieved / target) * 100

        # Find Slab
        applied_slab = self.db.query(IncentiveSlab).filter(
            IncentiveSlab.min_percentage <= percentage
        ).order_by(IncentiveSlab.min_percentage.desc()).first()

        amount_per_unit: Optional[float] = 0.0 # Initialize with default value
        total_incentive: float = 0.0 # Initialize with default value
        applied_slab_val = 0.0

        if applied_slab:
            amount_per_unit = applied_slab.amount_per_unit
            total_incentive = achieved * amount_per_unit
            applied_slab_val = applied_slab.min_percentage

        db_slip = IncentiveSlip(
            user_id=calc_in.user_id,
            period=calc_in.period,
            target=target,
            achieved=achieved,
            percentage=round(percentage, 2),
            applied_slab=applied_slab_val,
            amount_per_unit=amount_per_unit,
            total_incentive=round(total_incentive, 2),
            generated_at=datetime.now(UTC)
        )
        self.db.add(db_slip)
        self.db.commit()
        self.db.refresh(db_slip)

        # Attach user name for response
        res = IncentiveSlipRead.model_validate(db_slip)
        res.user_name = user.name or user.email
        return res

    def get_user_incentive_slips(self, user_id: int):
        slips = self.db.query(IncentiveSlip).filter(IncentiveSlip.user_id == user_id).all()
        results = []
        for s in slips:
            r = IncentiveSlipRead.model_validate(s)
            r.user_name = s.user.name or s.user.email
            results.append(r)
        return results


