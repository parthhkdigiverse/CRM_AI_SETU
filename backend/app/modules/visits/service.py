import os
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, UploadFile, Request
from beanie.operators import In

from app.modules.visits.models import Visit, VisitStatus
from app.modules.visits.schemas import VisitCreate, VisitUpdate
from app.modules.users.models import User, UserRole
from app.modules.shops.models import Shop
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType

BASE_DIR = Path(__file__).parent.parent.parent.parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads" / "visits"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class VisitService:
    def __init__(self):
        self.activity_logger = ActivityLogger()

    async def _enrich_visit(self, visit: Visit):
        if not visit: return
        shop = await Shop.find_one(Shop.id == visit.shop_id)
        user = await User.find_one(User.id == visit.user_id)
        if shop:
            visit.shop_name = shop.name
            visit.shop_status = str(shop.status.value if hasattr(shop.status, 'value') else shop.status)
            visit.shop_demo_stage = getattr(shop, 'demo_stage', 0)
            from app.modules.areas.models import Area
            area = await Area.find_one(Area.id == shop.area_id)
            if area: visit.area_name = area.name
            if shop.pm_id:
                pm = await User.find_one(User.id == shop.pm_id)
                if pm: visit.project_manager_name = pm.name or pm.email
        if user:
            visit.user_name = user.name or user.email

    async def get_visit(self, visit_id: str):
        visit = await Visit.find_one(Visit.id == visit_id, Visit.is_deleted != True)
        if visit: await self._enrich_visit(visit)
        return visit

    async def get_visits(self, skip: int = 0, limit: int = 100, current_user: User = None, shop_id: str = None, user_id: str | None = None):
        query_filter = [Visit.is_deleted != True]
        if shop_id: query_filter.append(Visit.shop_id == shop_id)
        if user_id is not None: query_filter.append(Visit.user_id == user_id)

        if current_user and current_user.role != UserRole.ADMIN:
            owned_shops = await Shop.find(Shop.owner_id == current_user.id).to_list()
            assigned_shops = await Shop.find(In(Shop.assigned_owners_ids, [current_user.id])).to_list()
            relevant_shop_ids = list(set([s.id for s in owned_shops] + [s.id for s in assigned_shops]))
            query_filter.append({"$or": [
                {"user_id": current_user.id},
                {"shop_id": {"$in": relevant_shop_ids}}
            ]})

        visits = await Visit.find(*query_filter).sort(-Visit.visit_date).skip(skip).limit(limit).to_list()
        for v in visits:
            await self._enrich_visit(v)
        return visits

    async def create_visit(self, visit_in: VisitCreate, current_user: User, request: Request, photo: UploadFile = None):
        shop = await Shop.find_one(Shop.id == visit_in.shop_id)
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")
            
        visit_data = visit_in.model_dump()
        target_date = visit_data.get('visit_date') or datetime.now(timezone.utc)
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        existing = await Visit.find_one(
            Visit.shop_id == visit_in.shop_id,
            Visit.user_id == current_user.id,
            Visit.visit_date >= start_of_day,
            Visit.visit_date <= end_of_day,
            Visit.is_deleted != True
        )
        if existing:
            raise HTTPException(status_code=400, detail="A visit has already been logged for this shop today by the current user.")

        visit = Visit(**visit_data, user_id=current_user.id)
        if photo:
            try:
                ext = photo.filename.split(".")[-1]
                fname = f"visit_{visit_in.shop_id}_{current_user.id}_{int(datetime.now(timezone.utc).timestamp())}.{ext}"
                fpath = UPLOAD_DIR / fname
                with fpath.open("wb") as buf:
                    shutil.copyfileobj(photo.file, buf)
                visit.photo_url = f"/static/uploads/visits/{fname}"
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to upload photo: {str(e)}")

        await visit.insert()
        await self._enrich_visit(visit)

        # Pipeline transition
        from app.core.enums import MasterPipelineStage
        current_stage = shop.pipeline_stage
        new_stage = None
        if current_stage == MasterPipelineStage.LEAD: new_stage = MasterPipelineStage.PITCHING
        if visit.status == VisitStatus.SATISFIED and current_stage == MasterPipelineStage.PITCHING:
            new_stage = MasterPipelineStage.DELIVERY
        
        if new_stage and new_stage != current_stage:
            shop.pipeline_stage = new_stage
            await shop.save()

        await self.activity_logger.log_activity(
            user_id=current_user.id, user_role=current_user.role, action=ActionType.CREATE,
            entity_type=EntityType.VISIT, entity_id=visit.id, new_data=visit_in.model_dump(mode='json'), request=request
        )
        return visit

    async def update_visit(self, visit_id: str, visit_in: VisitUpdate, current_user: User, request: Request):
        visit = await self.get_visit(visit_id)
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")

        old_data = {"status": str(visit.status), "remarks": visit.remarks}
        update_data = visit_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(visit, field, value)
        await visit.save()

        await self.activity_logger.log_activity(
            user_id=current_user.id, user_role=current_user.role, action=ActionType.UPDATE,
            entity_type=EntityType.VISIT, entity_id=visit.id, old_data=old_data, new_data=update_data, request=request
        )
        return visit
