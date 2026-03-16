# backend/app/modules/areas/service.py
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

    def get_areas(self, current_user: User, skip: int = 0, limit: int = 100):
        from sqlalchemy.orm import selectinload
        query = self.db.query(Area).options(
            selectinload(Area.assigned_users_list),
            selectinload(Area.archived_by),
            selectinload(Area.creator)
        ).filter(Area.is_archived == False)

        # If Admin, return all active (non-archived) areas
        if current_user.role == "ADMIN":
            areas = query.offset(skip).limit(limit).all()
        else:
            # Sales/Telesales: Check the many-to-many relationship
            areas = query.filter(
                Area.assigned_users_list.any(User.id == current_user.id)
            ).offset(skip).limit(limit).all()

        for area in areas:
            # We add shops_count dynamically to the model 
            setattr(area, 'shops_count', len([s for s in getattr(area, 'shops', []) if not getattr(s, 'is_archived', False)]) if getattr(area, 'shops', None) else 0)
            setattr(area, 'archived_by_name', area.archived_by.name if getattr(area, 'archived_by', None) else None)
            setattr(area, 'created_by_name', area.creator.name if getattr(area, 'creator', None) else None)
            assigned_users = [
                {"id": u.id, "name": u.name, "role": getattr(u.role, 'value', str(u.role)) if u.role else None} 
                for u in getattr(area, 'assigned_users_list', [])
            ]
            setattr(area, 'assigned_users', assigned_users)
        return areas

    # ── Accept Area (Staff claims the area) ──
    def accept_area(self, area_id: int, current_user: User):
        from sqlalchemy.orm import joinedload
        area = self.db.query(Area).options(joinedload(Area.shops)).filter(Area.id == area_id).first()
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
            
        if not any(u.id == current_user.id for u in area.assigned_users_list):
            raise HTTPException(status_code=403, detail="You are not assigned to this area.")
            
        from datetime import datetime, UTC
        db_user = self.db.query(User).filter(User.id == current_user.id).first()
        area.assignment_status = "ACCEPTED"
        area.assigned_users_list = [db_user]
        area.accepted_at = datetime.now(UTC)
        
        for shop in area.shops:
            shop.assignment_status = "ACCEPTED"
            shop.assigned_owners_list = [db_user]
            shop.accepted_at = datetime.now(UTC)
        
        self.db.commit()
        self.db.refresh(area)
        
        setattr(area, 'shops_count', len(area.shops) if getattr(area, 'shops', None) else 0)
        setattr(area, 'archived_by_name', area.archived_by.name if getattr(area, 'archived_by', None) else None)
        assigned_users_out = [
            {"id": u.id, "name": u.name, "role": getattr(u.role, 'value', str(u.role)) if u.role else None} 
            for u in getattr(area, 'assigned_users_list', [])
        ]
        setattr(area, 'assigned_users', assigned_users_out)
        return area

    def create_area(self, area_in: AreaCreate, current_user: User):
        from app.modules.users.models import UserRole
        from datetime import datetime, UTC
        
        area = Area(**area_in.model_dump())
        area.created_by_id = current_user.id
        
        # Auto-Assign if not Admin
        if current_user.role != UserRole.ADMIN:
            db_user = self.db.query(User).filter(User.id == current_user.id).first()
            area.assigned_users_list = [db_user]
            area.assignment_status = "ACCEPTED"
            area.accepted_at = datetime.now(UTC)
            area.assigned_by_id = current_user.id
        
        self.db.add(area)
        self.db.commit()
        self.db.refresh(area)
        
        setattr(area, 'shops_count', 0)
        setattr(area, 'archived_by_name', None)
        setattr(area, 'created_by_name', current_user.name)
        
        assigned_users = [
            {"id": u.id, "name": u.name, "role": getattr(u.role, 'value', str(u.role)) if u.role else None} 
            for u in getattr(area, 'assigned_users_list', [])
        ]
        setattr(area, 'assigned_users', assigned_users)
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
        setattr(area, 'shops_count', len(area.shops) if getattr(area, 'shops', None) else 0)
        setattr(area, 'archived_by_name', area.archived_by.name if getattr(area, 'archived_by', None) else None)
        assigned_users = [
            {"id": u.id, "name": u.name, "role": getattr(u.role, 'value', str(u.role)) if u.role else None} 
            for u in getattr(area, 'assigned_users_list', [])
        ]
        setattr(area, 'assigned_users', assigned_users)
        return area

    def assign_area(self, area_id: int, user_ids: List[int], current_user: User, shop_ids: List[int] = None):
        if not user_ids:
            raise HTTPException(status_code=400, detail="At least one user must be selected for assignment.")
            
        area = self.db.query(Area).filter(Area.id == area_id).first()
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        
        users = self.db.query(User).filter(User.id.in_(user_ids)).all()
        if not users or len(users) != len(user_ids):
            raise HTTPException(status_code=404, detail="One or more users not found")

        current_user_ids = {u.id for u in area.assigned_users_list}
        new_user_ids = {u.id for u in users}
        
        if len(new_user_ids) > 1 or new_user_ids != current_user_ids:
            area.assignment_status = "PENDING"
            area.assigned_by_id = current_user.id
            area.accepted_at = None

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
                if len(new_user_ids) > 1 or new_user_ids != current_user_ids:
                    shop.assignment_status = "PENDING"
                    shop.assigned_by_id = current_user.id
                    shop.accepted_at = None
            
            # Make sure all assigned users are also granted access to the parent Area
            # This ensures the Area shows up in their Navigation Sidebar
            for user in users:
                if user not in area.assigned_users_list:
                    area.assigned_users_list.append(user)
                    
            # Optionally update the primary owner of the Area if not set
            if not area.assigned_user_id:
                 area.assigned_user_id = primary_owner_id
                 
        else:
            # Full assignment: Update area and ALL shops
            area.assigned_user_id = primary_owner_id
            area.assigned_users_list = users
            
            all_shops = self.db.query(Shop).filter(Shop.area_id == area_id).all()
            for shop in all_shops:
                shop.owner_id = primary_owner_id
                shop.assigned_owners_list = users
                if len(new_user_ids) > 1 or new_user_ids != current_user_ids:
                    shop.assignment_status = "PENDING"
                    shop.assigned_by_id = current_user.id
                    shop.accepted_at = None
        
        self.db.commit()
        self.db.refresh(area)
        setattr(area, 'shops_count', len(area.shops) if getattr(area, 'shops', None) else 0)
        setattr(area, 'archived_by_name', area.archived_by.name if getattr(area, 'archived_by', None) else None)
        assigned_users_out = [
            {"id": u.id, "name": u.name, "role": getattr(u.role, 'value', str(u.role)) if u.role else None} 
            for u in getattr(area, 'assigned_users_list', [])
        ]
        setattr(area, 'assigned_users', assigned_users_out)
        return area

    # ── Soft Delete (Archive) ──
    def archive_area(self, area_id: int, current_user: User):
        area = self.db.query(Area).filter(Area.id == area_id).first()
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        
        # Check permissions
        if current_user.role != "ADMIN":
            if not any(u.id == current_user.id for u in area.assigned_users_list):
                raise HTTPException(status_code=403, detail="Not authorized to archive this area")
        
        area.is_archived = True
        area.archived_by_id = current_user.id
        # Also archive all child shops
        self.db.query(Shop).filter(Shop.area_id == area_id).update(
            {Shop.is_archived: True, Shop.archived_by_id: current_user.id}, synchronize_session=False
        )
        
        self.db.commit()
        return {"detail": f"Area \"{area.name}\" and its shops have been archived"}

    # ── Archived Listing (Scoped) ──
    def get_archived_areas(self, current_user: User):
        from sqlalchemy.orm import selectinload
        query = self.db.query(Area).options(
            selectinload(Area.assigned_users_list),
            selectinload(Area.archived_by),
            selectinload(Area.creator)
        ).filter(Area.is_archived == True)

        if current_user.role == "ADMIN":
            areas = query.all()
        else:
            areas = query.filter(
                (Area.archived_by_id == current_user.id) | (Area.assigned_users_list.any(User.id == current_user.id))
            ).all()

        for area in areas:
            setattr(area, 'shops_count', len(area.shops) if area.shops else 0)
            setattr(area, 'archived_by_name', area.archived_by.name if area.archived_by else None)
            setattr(area, 'created_by_name', area.creator.name if getattr(area, 'creator', None) else None)
            assigned_users = [
                {"id": u.id, "name": u.name, "role": getattr(u.role, 'value', str(u.role)) if u.role else None} 
                for u in getattr(area, 'assigned_users_list', [])
            ]
            setattr(area, 'assigned_users', assigned_users)
        return areas

    # ── Unarchive ──
    def unarchive_area(self, area_id: int, current_user: User):
        area = self.db.query(Area).filter(Area.id == area_id).first()
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        
        # Check permissions
        if current_user.role != "ADMIN":
            if area.archived_by_id != current_user.id and not any(u.id == current_user.id for u in area.assigned_users_list):
                 raise HTTPException(status_code=403, detail="Not authorized to unarchive this area")
        
        area.is_archived = False
        area.archived_by_id = None
        # Also unarchive child shops
        self.db.query(Shop).filter(Shop.area_id == area_id).update(
            {Shop.is_archived: False, Shop.archived_by_id: None}, synchronize_session=False
        )
        
        self.db.commit()
        self.db.refresh(area)
        setattr(area, 'shops_count', len(area.shops) if area.shops else 0)
        setattr(area, 'archived_by_name', None)
        # Load assigned users again for the response model
        assigned_users = [
            {"id": u.id, "name": u.name, "role": getattr(u.role, 'value', str(u.role)) if u.role else None} 
            for u in getattr(area, 'assigned_users_list', [])
        ]
        setattr(area, 'assigned_users', assigned_users)
        return area

    # ── Hard Delete (Admin only) ──
    def hard_delete_area(self, area_id: int):
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
