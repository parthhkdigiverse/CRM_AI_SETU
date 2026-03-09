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
        areas = self.db.query(Area).offset(skip).limit(limit).all()
        for area in areas:
            # We add shops_count dynamically to the model 
            setattr(area, 'shops_count', len(area.shops) if area.shops else 0)
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

    def assign_area(self, area_id: int, user_ids: List[int], shop_ids: List[int] = None):
        if not user_ids:
            raise HTTPException(status_code=400, detail="At least one user must be selected for assignment.")
            
        area = self.db.query(Area).filter(Area.id == area_id).first()
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        
        users = self.db.query(User).filter(User.id.in_(user_ids)).all()
        if not users or len(users) != len(user_ids):
            raise HTTPException(status_code=404, detail="One or more users not found")

        primary_owner_id = user_ids[0]
        from app.modules.shops.models import Shop
        
        if shop_ids is not None:
            # Granular assignment: Update specific shops only
            shops_to_assign = self.db.query(Shop).filter(
                Shop.area_id == area_id,
                Shop.id.in_(shop_ids)
            ).all()
            
            for shop in shops_to_assign:
                shop.owner_id = primary_owner_id
                # Replace existing assignments with the new list to maintain accurate sync
                shop.assigned_owners_list = users
                
        else:
            # Full assignment: Update area and ALL shops
            area.assigned_user_id = primary_owner_id
            area.assigned_users_list = users
            
            all_shops = self.db.query(Shop).filter(Shop.area_id == area_id).all()
            for shop in all_shops:
                shop.owner_id = primary_owner_id
                shop.assigned_owners_list = users
        
        self.db.commit()
        self.db.refresh(area)
        return area

    def delete_area(self, area_id: int):
        area = self.db.query(Area).filter(Area.id == area_id).first()
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        
        # Cascading delete: Remove all shops associated with this area
        from app.modules.shops.models import Shop
        self.db.query(Shop).filter(Shop.area_id == area_id).delete()
        
        self.db.delete(area)
        self.db.commit()
        return {"detail": "Area and associated shops deleted"}
