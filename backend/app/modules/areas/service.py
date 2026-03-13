from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.modules.areas.models import Area
from app.modules.areas.schemas import AreaCreate
from app.modules.users.models import User
from app.modules.shops.models import Shop 

class AreaService:
    def __init__(self, db: Session):
        self.db = db

    def get_areas(self, skip: int = 0, limit: int = 100):
        query = self.db.query(Area).filter(Area.is_deleted == False)
        
        areas = query.offset(skip).limit(limit).all()
        for area in areas:
            # Only count non-deleted shops
            active_shops = [s for s in (area.shops or []) if not getattr(s, 'is_deleted', False)]
            setattr(area, 'shops_count', len(active_shops))
        return areas

    def create_area(self, area_in: AreaCreate):
        area = Area(**area_in.model_dump())
        self.db.add(area)
        self.db.commit()
        self.db.refresh(area)
        return area

    def update_area(self, area_id: int, area_in):
        area = self.db.query(Area).filter(Area.id == area_id).first()
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        update_data = area_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(area, field, value)
        self.db.commit()
        self.db.refresh(area)
        setattr(area, 'shops_count', len(area.shops) if area.shops else 0)
        return area

    def assign_area(self, area_id: int, user_id: int, shop_ids: List[int] = None):
        area = self.db.query(Area).filter(Area.id == area_id).first()
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        from app.modules.shops.models import Shop
        
        if shop_ids is not None:
            # Granular assignment: Update owner_id ONLY for specific shops
            # Ensure the shops belong to the specified area
            self.db.query(Shop).filter(
                Shop.area_id == area_id,
                Shop.id.in_(shop_ids)
            ).update({"owner_id": user_id}, synchronize_session=False)
        else:
            # Full assignment: Update area and ALL shops
            area.assigned_user_id = user_id
            self.db.query(Shop).filter(Shop.area_id == area_id).update({"owner_id": user_id}, synchronize_session=False)
        
        self.db.commit()
        self.db.refresh(area)
        return area

    def delete_area(self, area_id: int):
        area = self.db.query(Area).filter(Area.id == area_id).first()
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        
        from app.modules.salary.models import AppSetting
        policy = self.db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
        is_hard = policy and policy.value == "HARD"

        if is_hard:
            # Cascading delete: Remove all shops associated with this area
            from app.modules.shops.models import Shop
            self.db.query(Shop).filter(Shop.area_id == area_id).delete()
            self.db.delete(area)
        else:
            area.is_deleted = True
            # Soft delete associated shops too
            from app.modules.shops.models import Shop
            self.db.query(Shop).filter(Shop.area_id == area_id).update({"is_deleted": True}, synchronize_session=False)

        self.db.commit()
        return {"detail": f"Area and associated shops {'permanently ' if is_hard else ''}deleted"}
