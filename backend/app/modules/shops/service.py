from fastapi import HTTPException
from app.modules.shops.models import Shop
from app.core.enums import MasterPipelineStage, GlobalTaskStatus
from app.modules.shops.schemas import ShopCreate, ShopUpdate
from app.modules.clients.models import Client
from app.modules.users.models import User, UserRole
import logging
import random

logger = logging.getLogger(__name__)

class ShopService:

    async def _enrich_shop(self, shop: Shop) -> dict:
        shop_data = {}
        if shop.owner_id:
            owner = await User.find_one(User.id == shop.owner_id)
            shop_data["owner_name"] = owner.name if owner else None
        else:
            shop_data["owner_name"] = None
        if shop.area_id:
            from app.modules.areas.models import Area
            area = await Area.find_one(Area.id == shop.area_id)
            shop_data["area_name"] = area.name if area else None
        else:
            shop_data["area_name"] = None
        if shop.created_by_id:
            creator = await User.find_one(User.id == shop.created_by_id)
            shop_data["created_by_name"] = creator.name if creator else None
        else:
            shop_data["created_by_name"] = None
        if shop.project_manager_id:
            pm = await User.find_one(User.id == shop.project_manager_id)
            shop_data["project_manager_name"] = pm.name if pm else None
        else:
            shop_data["project_manager_name"] = None
        assigned_users = []
        for uid in (shop.assigned_owners_list or []):
            user = await User.find_one(User.id == uid)
            if user:
                assigned_users.append({"id": user.id, "name": user.name, "role": getattr(user.role, "value", str(user.role))})
        shop_data["assigned_users"] = assigned_users
        shop_data["archived_by_name"] = None
        shop_data["last_visitor_name"] = None
        shop_data["last_visit_status"] = None
        return shop_data

    async def create_shop(self, shop_in: ShopCreate, current_user: User) -> Shop:
        from datetime import datetime, timezone
        shop_data = shop_in.model_dump()
        shop = Shop(**shop_data)
        shop.created_by_id = current_user.id
        shop.project_manager_id = getattr(shop_in, 'project_manager_id', None) or current_user.id
        if current_user.role != UserRole.ADMIN:
            shop.assigned_owner_ids = [current_user.id]
            shop.assignment_status = "ACCEPTED"
            shop.accepted_at = datetime.now(timezone.utc)
            shop.assigned_by_id = current_user.id
        await shop.insert()
        enriched = await self._enrich_shop(shop)
        for k, v in enriched.items():
            setattr(shop, k, v)
        return shop

    async def get_shop(self, shop_id: str) -> Shop:
        shop = await Shop.find_one(Shop.id == shop_id, Shop.is_deleted != True)
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")
        enriched = await self._enrich_shop(shop)
        for k, v in enriched.items():
            setattr(shop, k, v)
        return shop

    async def list_shops(self, current_user: User, skip: int = 0, limit: int = 100, pipeline_stage: MasterPipelineStage = None, owner_id: int = None):
        from app.modules.salary.models import AppSetting
        policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
        query_filter = []
        if not policy or policy.value == "SOFT":
            query_filter.append(Shop.is_deleted != True)
        if pipeline_stage:
            query_filter.append(Shop.pipeline_stage == pipeline_stage)
        if current_user.role != UserRole.ADMIN:
            query_filter.append(Shop.assigned_owner_ids == current_user.id)
        elif owner_id:
            query_filter.append(Shop.owner_id == owner_id)
        shops = await Shop.find(*query_filter).skip(skip).limit(limit).to_list()
        result = []
        for shop in shops:
            enriched = await self._enrich_shop(shop)
            shop_dict = shop.model_dump()
            shop_dict.update(enriched)
            result.append(shop_dict)
        return result

    async def list_kanban_shops(self, owner_id: int = None, source: str = None):
        query_filter = [Shop.is_deleted != True]
        if owner_id:
            query_filter.append(Shop.owner_id == owner_id)
        if source and source not in {"ALL", "all"}:
            query_filter.append(Shop.source == source)
        shops = await Shop.find(*query_filter).to_list()
        kanban = {"LEAD": [], "PITCHING": [], "NEGOTIATION": [], "DELIVERY": [], "MAINTENANCE": []}
        for shop in shops:
            enriched = await self._enrich_shop(shop)
            shop_dict = shop.model_dump()
            shop_dict.update(enriched)
            from app.modules.visits.models import Visit
            visits = await Visit.find(Visit.shop_id == shop.id).to_list()
            if visits:
                latest_visit = max(visits, key=lambda v: v.visit_date or v.created_at)
                raw_status = latest_visit.status
                shop_dict["last_visit_status"] = raw_status.value if hasattr(raw_status, "value") else str(raw_status)
                visitor = await User.find_one(User.id == latest_visit.user_id)
                shop_dict["last_visitor_name"] = visitor.name if visitor else None
            stage_val = str(shop.pipeline_stage.value) if hasattr(shop.pipeline_stage, "value") else str(shop.pipeline_stage)
            if stage_val in kanban:
                kanban[stage_val].append(shop_dict)
        return kanban

    async def update_shop(self, shop_id: str, shop_in: ShopUpdate) -> Shop:
        shop = await self.get_shop(shop_id)
        update_data = shop_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(shop, field, value)
        await shop.save()
        return shop

    async def approve_pipeline_entry(self, shop_id: str):
        shop = await self.get_shop(shop_id)
        if shop.pipeline_stage == MasterPipelineStage.DELIVERY:
            raise HTTPException(status_code=400, detail="Entry already approved")
        existing_client = None
        if shop.email:
            existing_client = await Client.find_one(Client.email == shop.email)
        if not existing_client and shop.phone:
            existing_client = await Client.find_one(Client.phone == shop.phone)
        if existing_client:
            shop.pipeline_stage = MasterPipelineStage.DELIVERY
            await shop.save()
            return existing_client
        db_client = Client(name=shop.contact_person or shop.name, email=shop.email or f"converted_{shop.id}@crm.internal", phone=shop.phone, organization=shop.name, owner_id=shop.owner_id)
        await db_client.insert()
        shop.pipeline_stage = MasterPipelineStage.DELIVERY
        await shop.save()
        return db_client

    async def archive_shop(self, shop_id: str, current_user: User):
        shop = await self.get_shop(shop_id)
        if current_user.role != UserRole.ADMIN:
            if current_user.id not in (shop.assigned_owner_ids or []):
                raise HTTPException(status_code=403, detail="Not authorized to archive this shop")
        shop.is_deleted = True
        await shop.save()
        return {"detail": f"Shop \"{shop.name}\" has been archived"}

    async def get_archived_shops(self, current_user: User):
        query_filter = [Shop.is_deleted == True]
        if current_user.role != UserRole.ADMIN:
            query_filter.append(Shop.assigned_owner_ids == current_user.id)
        shops = await Shop.find(*query_filter).to_list()
        result = []
        for shop in shops:
            enriched = await self._enrich_shop(shop)
            shop_dict = shop.model_dump()
            shop_dict.update(enriched)
            result.append(shop_dict)
        return result

    async def unarchive_shop(self, shop_id: str, current_user: User):
        shop = await Shop.find_one(Shop.id == shop_id)
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")
        if current_user.role != UserRole.ADMIN:
            if current_user.id not in (shop.assigned_owner_ids or []):
                raise HTTPException(status_code=403, detail="Not authorized to unarchive this shop")
        shop.is_deleted = False
        await shop.save()
        return shop

    async def hard_delete_shop(self, shop_id: str):
        shop = await Shop.find_one(Shop.id == shop_id)
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")
        if shop.email:
            client = await Client.find_one(Client.email == shop.email)
            if client:
                raise HTTPException(status_code=400, detail="Cannot delete shop converted to client")
        if shop.phone:
            client = await Client.find_one(Client.phone == shop.phone)
            if client:
                raise HTTPException(status_code=400, detail="Cannot delete shop converted to client")
        from app.modules.salary.models import AppSetting
        policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
        is_hard = policy and policy.value == "HARD"
        if is_hard:
            await shop.delete()
        else:
            shop.is_deleted = True
            await shop.save()
        return {"detail": "Shop deleted"}

    async def accept_shop(self, shop_id: str, current_user: User):
        from datetime import datetime, timezone
        shop = await Shop.find_one(Shop.id == shop_id)
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")
        if current_user.id not in (shop.assigned_owner_ids or []):
            raise HTTPException(status_code=403, detail="You are not assigned to this shop.")
        shop.assignment_status = "ACCEPTED"
        shop.assigned_owner_ids = [current_user.id]
        shop.accepted_at = datetime.now(timezone.utc)
        await shop.save()
        enriched = await self._enrich_shop(shop)
        shop_dict = shop.model_dump()
        shop_dict.update(enriched)
        return shop_dict

    async def get_accepted_leads(self, current_user: User):
        from app.modules.visits.models import Visit
        from app.modules.areas.models import Area
        query_filter = [Shop.assignment_status == "ACCEPTED", Shop.pipeline_stage == MasterPipelineStage.LEAD]
        if current_user.role != UserRole.ADMIN:
            query_filter.append(Shop.assigned_owner_ids == current_user.id)
        shops = await Shop.find(*query_filter).sort(-Shop.accepted_at).to_list()
        history = []
        for shop in shops:
            if current_user.role == UserRole.ADMIN:
                visited = await Visit.find_one(Visit.shop_id == shop.id)
            else:
                visited = await Visit.find_one(Visit.shop_id == shop.id, Visit.user_id == current_user.id)
            if visited:
                continue
            area = await Area.find_one(Area.id == shop.area_id) if shop.area_id else None
            assigned_name = None
            if shop.assigned_owner_ids:
                u = await User.find_one(User.id == shop.assigned_owner_ids[0])
                assigned_name = u.name if u else "Unknown"
            assigned_by = None
            if shop.assigned_by_id:
                ab = await User.find_one(User.id == shop.assigned_by_id)
                assigned_by = ab.name if ab else "System"
            history.append({"shop_id": shop.id, "area_name": area.name if area else "N/A", "shop_name": shop.name, "assigned_to_name": assigned_name or "Unknown", "assigned_by_name": assigned_by or "System", "accepted_at": shop.accepted_at})
        return history

    async def assign_pm(self, shop_id: str, pm_id: str, current_user: User):
        shop = await Shop.find_one(Shop.id == shop_id, Shop.is_deleted != True)
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")
        pm = await User.find_one(User.id == pm_id)
        if not pm:
            raise HTTPException(status_code=404, detail="User not found")
        if pm.role not in [UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]:
            raise HTTPException(status_code=400, detail="Selected user is not a Project Manager or Admin")
        shop.project_manager_id = pm_id
        await shop.save()
        enriched = await self._enrich_shop(shop)
        shop_dict = shop.model_dump()
        shop_dict.update(enriched)
        return shop_dict

    async def auto_assign_shop(self, shop_id: str, current_user: User):
        from app.modules.projects.models import Project
        shop = await Shop.find_one(Shop.id == shop_id, Shop.is_deleted != True)
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")
        pms = await User.find(User.is_active == True, User.role.in_([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])).to_list()
        if not pms:
            raise HTTPException(status_code=400, detail="No active Project Managers found")
        pm_scores = {}
        for pm in pms:
            sc = await Shop.find(Shop.project_manager_id == pm.id, Shop.is_deleted != True, Shop.pipeline_stage.in_([MasterPipelineStage.LEAD, MasterPipelineStage.PITCHING])).count()
            pc = await Project.find(Project.pm_id == pm.id, Project.status.in_([GlobalTaskStatus.OPEN, GlobalTaskStatus.IN_PROGRESS])).count()
            pm_scores[pm.id] = sc + pc
        min_score = min(pm_scores.values())
        tied_pms = [pm_id for pm_id, score in pm_scores.items() if score == min_score]
        selected_pm_id = random.choice(tied_pms)
        selected_pm = next((pm for pm in pms if pm.id == selected_pm_id), None)
        shop.project_manager_id = selected_pm_id
        await shop.save()
        enriched = await self._enrich_shop(shop)
        shop_dict = shop.model_dump()
        shop_dict.update(enriched)
        return shop_dict

    async def suggest_least_busy_pm(self, current_user: User):
        from app.modules.projects.models import Project
        pms = await User.find(User.is_active == True, User.role.in_([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])).to_list()
        if not pms:
            raise HTTPException(status_code=400, detail="No active Project Managers found")
        pm_scores = {}
        for pm in pms:
            sc = await Shop.find(Shop.project_manager_id == pm.id, Shop.is_deleted != True, Shop.pipeline_stage.in_([MasterPipelineStage.LEAD, MasterPipelineStage.PITCHING])).count()
            pc = await Project.find(Project.pm_id == pm.id, Project.status.in_([GlobalTaskStatus.OPEN, GlobalTaskStatus.IN_PROGRESS])).count()
            pm_scores[pm.id] = sc + pc
        min_score = min(pm_scores.values())
        tied_pms = [pm_id for pm_id, score in pm_scores.items() if score == min_score]
        selected_pm_id = random.choice(tied_pms)
        selected_pm = next((pm for pm in pms if pm.id == selected_pm_id), None)
        return {"suggested_pm_id": selected_pm.id, "name": selected_pm.name}

    async def complete_demo(self, shop_id: str, current_user: User):
        shop = await Shop.find_one(Shop.id == shop_id, Shop.is_deleted != True)
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")
        shop.demo_stage = (shop.demo_stage or 0) + 1
        shop.demo_scheduled_at = None
        if shop.demo_stage == 1:
            shop.pipeline_stage = MasterPipelineStage.PITCHING
        await shop.save()
        enriched = await self._enrich_shop(shop)
        shop_dict = shop.model_dump()
        shop_dict.update(enriched)
        return shop_dict

    async def cancel_demo(self, shop_id: str, current_user: User):
        shop = await Shop.find_one(Shop.id == shop_id, Shop.is_deleted != True)
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")
        shop.demo_scheduled_at = None
        shop.demo_title = None
        shop.demo_type = None
        shop.demo_notes = None
        shop.demo_meet_link = None
        await shop.save()
        enriched = await self._enrich_shop(shop)
        shop_dict = shop.model_dump()
        shop_dict.update(enriched)
        return shop_dict

    async def schedule_demo(self, shop_id: str, payload, current_user: User):
        shop = await Shop.find_one(Shop.id == shop_id, Shop.is_deleted != True)
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")
        shop.demo_scheduled_at = payload.scheduled_at
        shop.demo_title = payload.title
        shop.demo_type = payload.demo_type
        shop.demo_notes = payload.notes
        if payload.demo_type == "Google Meet":
            from app.utils.google_meet import generate_google_meet_link
            try:
                result = generate_google_meet_link(title=payload.title or f"Demo: {shop.name}", start_time=payload.scheduled_at, description=payload.notes or "")
                shop.demo_meet_link = result.get("meet_link")
            except Exception as e:
                print(f"[ShopService] Failed to generate Google Meet link: {e}")
                shop.demo_meet_link = None
        else:
            shop.demo_meet_link = None
        await shop.save()
        enriched = await self._enrich_shop(shop)
        shop_dict = shop.model_dump()
        shop_dict.update(enriched)
        return shop_dict

    async def get_demo_queue(self, current_user: User):
        query_filter = [Shop.is_deleted != True, Shop.project_manager_id != None]
        if current_user.role != UserRole.ADMIN:
            query_filter.append(Shop.project_manager_id == current_user.id)
        shops = await Shop.find(*query_filter).sort(-Shop.id).to_list()
        result = []
        for shop in shops:
            enriched = await self._enrich_shop(shop)
            shop_dict = shop.model_dump()
            shop_dict.update(enriched)
            result.append(shop_dict)
        return result

    async def get_pm_pipeline_analytics(self):
        shops = await Shop.find(Shop.is_deleted != True, Shop.project_manager_id != None).to_list()
        pm_stats = {}
        for shop in shops:
            pm = await User.find_one(User.id == shop.project_manager_id)
            pm_name = pm.name if pm else "Unknown"
            if pm_name not in pm_stats:
                pm_stats[pm_name] = {"pm_name": pm_name, "in_demo": 0, "meeting_set": 0, "converted": 0}
            if shop.pipeline_stage == MasterPipelineStage.DELIVERY:
                pm_stats[pm_name]["converted"] += 1
            elif shop.pipeline_stage == MasterPipelineStage.PITCHING:
                pm_stats[pm_name]["meeting_set"] += 1
            else:
                pm_stats[pm_name]["in_demo"] += 1
        return list(pm_stats.values())
