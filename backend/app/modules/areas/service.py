from typing import List, Optional
from fastapi import HTTPException
from app.modules.areas.models import Area
from app.modules.areas.schemas import AreaCreate
from app.modules.users.models import User
from datetime import datetime, timezone

class AreaService:

    async def get_areas(self, current_user: User, skip: int = 0, limit: int = 100):
        if current_user.role == "ADMIN":
            areas = await Area.find(Area.is_deleted != True).skip(skip).limit(limit).to_list()
        else:
            areas = await Area.find(Area.is_deleted != True, Area.assigned_user_ids == current_user.id).skip(skip).limit(limit).to_list()
        for area in areas:
            await self._enrich_area(area)
        return areas

    async def _enrich_area(self, area: Area):
        from app.modules.shops.models import Shop
        shops = await Shop.find(Shop.area_id == area.id, Shop.is_deleted != True).to_list()
        area.shops_count = len(shops)
        assigned_users = []
        for uid in (area.assigned_user_ids or []):
            user = await User.find_one(User.id == uid)
            if user:
                assigned_users.append({"id": user.id, "name": user.name, "role": getattr(user.role, "value", str(user.role))})
        area.assigned_users = assigned_users
        if area.created_by_id:
            creator = await User.find_one(User.id == area.created_by_id)
            area.created_by_name = creator.name if creator else None

    async def accept_area(self, area_id: str, current_user: User):
        area = await Area.find_one(Area.id == area_id)
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        if current_user.id not in (area.assigned_user_ids or []):
            raise HTTPException(status_code=403, detail="You are not assigned to this area.")
        area.assignment_status = "ACCEPTED"
        area.assigned_user_ids = [current_user.id]
        area.accepted_at = datetime.now(timezone.utc)
        await area.save()
        from app.modules.shops.models import Shop
        shops = await Shop.find(Shop.area_id == area_id).to_list()
        for shop in shops:
            shop.assignment_status = "ACCEPTED"
            shop.assigned_owner_ids = [current_user.id]
            shop.accepted_at = datetime.now(timezone.utc)
            await shop.save()
        await self._enrich_area(area)
        return area

    async def create_area(self, area_in: AreaCreate, current_user: User):
        from app.modules.users.models import UserRole
        area_data = area_in.model_dump()
        area = Area(**area_data)
        area.created_by_id = current_user.id
        if current_user.role != UserRole.ADMIN:
            area.assigned_user_ids = [current_user.id]
            area.assignment_status = "ACCEPTED"
            area.accepted_at = datetime.now(timezone.utc)
            area.assigned_by_id = current_user.id
        await area.insert()
        await self._enrich_area(area)
        return area

    async def update_area(self, area_id: str, area_in):
        area = await Area.find_one(Area.id == area_id)
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        update_data = area_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(area, field, value)
        await area.save()
        await self._enrich_area(area)
        return area

    async def assign_area(self, area_id: str, user_ids: List[int], current_user: User, shop_ids: List[int] = None):
        if not user_ids:
            raise HTTPException(status_code=400, detail="At least one user must be selected for assignment.")
        area = await Area.find_one(Area.id == area_id)
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        users = []
        for uid in user_ids:
            user = await User.find_one(User.id == uid)
            if not user:
                raise HTTPException(status_code=404, detail=f"User {uid} not found")
            users.append(user)
        current_user_ids = set(area.assigned_user_ids or [])
        new_user_ids = set(user_ids)
        if len(new_user_ids) > 1 or new_user_ids != current_user_ids:
            area.assignment_status = "PENDING"
            area.assigned_by_id = current_user.id
            area.accepted_at = None
        from app.modules.shops.models import Shop
        if shop_ids is not None:
            shops = await Shop.find(Shop.area_id == area_id, Shop.id.in_(shop_ids)).to_list()
            for shop in shops:
                shop.owner_id = user_ids[0]
                shop.assigned_owner_ids = user_ids
                if len(new_user_ids) > 1 or new_user_ids != current_user_ids:
                    shop.assignment_status = "PENDING"
                    shop.assigned_by_id = current_user.id
                    shop.accepted_at = None
                await shop.save()
            for uid in user_ids:
                if uid not in (area.assigned_user_ids or []):
                    area.assigned_user_ids = list(set((area.assigned_user_ids or []) + [uid]))
            if not area.assigned_user_id:
                area.assigned_user_id = user_ids[0]
        else:
            area.assigned_user_id = user_ids[0]
            area.assigned_user_ids = user_ids
            all_shops = await Shop.find(Shop.area_id == area_id).to_list()
            for shop in all_shops:
                shop.owner_id = user_ids[0]
                shop.assigned_owner_ids = user_ids
                if len(new_user_ids) > 1 or new_user_ids != current_user_ids:
                    shop.assignment_status = "PENDING"
                    shop.assigned_by_id = current_user.id
                    shop.accepted_at = None
                await shop.save()
        await area.save()
        await self._enrich_area(area)
        return area

    async def archive_area(self, area_id: str, current_user: User):
        area = await Area.find_one(Area.id == area_id)
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        if current_user.role != "ADMIN":
            if current_user.id not in (area.assigned_user_ids or []):
                raise HTTPException(status_code=403, detail="Not authorized to archive this area")
        area.is_deleted = True
        await area.save()
        from app.modules.shops.models import Shop
        shops = await Shop.find(Shop.area_id == area_id).to_list()
        for shop in shops:
            shop.is_deleted = True
            await shop.save()
        return {"detail": f"Area and its shops have been archived"}

    async def get_archived_areas(self, current_user: User):
        if current_user.role == "ADMIN":
            areas = await Area.find(Area.is_deleted == True).to_list()
        else:
            areas = await Area.find(Area.is_deleted == True, Area.assigned_user_ids == current_user.id).to_list()
        for area in areas:
            await self._enrich_area(area)
        return areas

    async def unarchive_area(self, area_id: str, current_user: User):
        area = await Area.find_one(Area.id == area_id)
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        area.is_deleted = False
        await area.save()
        from app.modules.shops.models import Shop
        shops = await Shop.find(Shop.area_id == area_id).to_list()
        for shop in shops:
            shop.is_deleted = False
            await shop.save()
        await self._enrich_area(area)
        return area

    async def hard_delete_area(self, area_id: str):
        area = await Area.find_one(Area.id == area_id)
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        from app.modules.salary.models import AppSetting
        from app.modules.shops.models import Shop
        policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
        is_hard = policy and policy.value == "HARD"
        shops = await Shop.find(Shop.area_id == area_id).to_list()
        if is_hard:
            for shop in shops:
                await shop.delete()
            await area.delete()
        else:
            area.is_deleted = True
            await area.save()
            for shop in shops:
                shop.is_deleted = True
                await shop.save()
        return {"detail": f"Area and associated shops deleted"}
