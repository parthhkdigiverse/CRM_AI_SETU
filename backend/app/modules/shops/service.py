from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.modules.shops.models import Shop, ShopStatus
from app.modules.shops.schemas import ShopCreate, ShopUpdate
from app.modules.clients.models import Client
from app.modules.users.models import User
import logging

logger = logging.getLogger(__name__)

class ShopService:
    @staticmethod
    def create_shop(db: Session, shop_in: ShopCreate):
        db_shop = Shop(**shop_in.model_dump())
        db.add(db_shop)
        db.commit()
        db.refresh(db_shop)
        return db_shop

    @staticmethod
    def get_shop(db: Session, shop_id: int):
        shop = db.query(Shop).filter(Shop.id == shop_id).first()
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")
        if getattr(shop, 'area', None):
            setattr(shop, 'area_name', shop.area.name)
        return shop

    @staticmethod
    def list_shops(db: Session, current_user: User, skip: int = 0, limit: int = 100, status: ShopStatus = None, owner_id: int = None):
        from sqlalchemy.orm import selectinload
        query = db.query(Shop).options(
            selectinload(Shop.owner),
            selectinload(Shop.area),
            selectinload(Shop.assigned_owners_list),
            selectinload(Shop.archived_by)
        ).filter(Shop.is_archived == False)
        
        if status:
            query = query.filter(Shop.status == status)
            
        # If Admin, return all shops
        if current_user.role != "ADMIN":
            # Sales/Telesales: Check the many-to-many relationship
            query = query.filter(
                Shop.assigned_owners_list.any(User.id == current_user.id)
            )
        elif owner_id:
            # Admins can optionally filter by a specific owner
            query = query.filter(Shop.owner_id == owner_id)
        
        results = query.offset(skip).limit(limit).all()
        shops = []
        for shop in results:
            shop_data = shop.__dict__.copy()
            shop_data["owner_name"] = shop.owner.name if getattr(shop, 'owner', None) else None
            shop_data["area_name"] = shop.area.name if getattr(shop, 'area', None) else None
            shop_data["archived_by_name"] = shop.archived_by.name if getattr(shop, 'archived_by', None) else None
            shop_data.pop("_sa_instance_state", None)
            
            # Map assigned owners for frontend UI
            shop_data["assigned_users"] = [
                {"id": u.id, "name": u.name, "role": getattr(u.role, 'value', str(u.role)) if u.role else None} 
                for u in getattr(shop, 'assigned_owners_list', [])
            ]
            shops.append(shop_data)
        return shops
        
    @staticmethod
    def list_kanban_shops(db: Session, owner_id: int = None):
        from sqlalchemy.orm import selectinload
        query = db.query(Shop).options(
            selectinload(Shop.owner),
            selectinload(Shop.area),
            selectinload(Shop.assigned_owners_list),
            selectinload(Shop.archived_by)
        ).filter(Shop.is_archived == False)
        
        if owner_id:
            query = query.filter(Shop.owner_id == owner_id)
            
        results = query.all()
        
        kanban = {
            "NEW": [],
            "CONTACTED": [],
            "MEETING_SET": [],
            "CONVERTED": [],
        }
        
        for shop in results:
            shop_data = shop.__dict__.copy()
            shop_data["owner_name"] = shop.owner.name if getattr(shop, 'owner', None) else None
            shop_data["area_name"] = shop.area.name if getattr(shop, 'area', None) else None
            shop_data["archived_by_name"] = shop.archived_by.name if getattr(shop, 'archived_by', None) else None
            shop_data.pop("_sa_instance_state", None)
            
            shop_data["assigned_users"] = [
                {"id": u.id, "name": u.name, "role": getattr(u.role, 'value', str(u.role)) if u.role else None} 
                for u in getattr(shop, 'assigned_owners_list', [])
            ]
            
            status_val = str(shop.status.value) if hasattr(shop.status, "value") else str(shop.status)
            if status_val in kanban:
                kanban[status_val].append(shop_data)
                
        return kanban


    @staticmethod
    def update_shop(db: Session, shop_id: int, shop_in: ShopUpdate):
        db_shop = ShopService.get_shop(db, shop_id)
        update_data = shop_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_shop, field, value)
        
        db.commit()
        db.refresh(db_shop)
        return db_shop

    @staticmethod
    def approve_pipeline_entry(db: Session, shop_id: int):
        db_shop = ShopService.get_shop(db, shop_id)
        
        if db_shop.status == ShopStatus.CONVERTED:
            raise HTTPException(status_code=400, detail="Entry already approved and converted to project")
            
        # Check if client already exists with this email/phone
        from sqlalchemy import or_
        existing_client = db.query(Client).filter(
            or_(
                Client.email == db_shop.email if db_shop.email else False,
                Client.phone == db_shop.phone if db_shop.phone else False
            )
        ).first()
        
        if existing_client:
            db_shop.status = ShopStatus.CONVERTED
            db.commit()
            return existing_client

        # Create new client
        db_client = Client(
            name=db_shop.contact_person or db_shop.name,
            email=db_shop.email or f"converted_{db_shop.id}@crm.internal", # Fallback email if missing
            phone=db_shop.phone,
            organization=db_shop.name,
            owner_id=db_shop.owner_id
        )
        
        db.add(db_client)
        db_shop.status = ShopStatus.CONVERTED
        
        db.commit()
        db.refresh(db_client)
        return db_client

    # ── Soft Delete (Archive) ──
    @staticmethod
    def archive_shop(db: Session, shop_id: int, current_user: User):
        db_shop = ShopService.get_shop(db, shop_id)

        # Check permissions
        if current_user.role != "ADMIN":
            if not any(u.id == current_user.id for u in db_shop.assigned_owners_list):
                 raise HTTPException(status_code=403, detail="Not authorized to archive this shop")

        db_shop.is_archived = True
        db_shop.archived_by_id = current_user.id
        db.commit()
        return {"detail": f"Shop \"{db_shop.name}\" has been archived"}

    # ── Archived Listing ──
    @staticmethod
    def get_archived_shops(db: Session, current_user: User):
        from sqlalchemy.orm import selectinload
        
        query = db.query(Shop).options(
            selectinload(Shop.owner),
            selectinload(Shop.area),
            selectinload(Shop.assigned_owners_list),
            selectinload(Shop.archived_by)
        ).filter(Shop.is_archived == True)

        if current_user.role != "ADMIN":
            query = query.filter(
                (Shop.archived_by_id == current_user.id) | (Shop.assigned_owners_list.any(User.id == current_user.id))
            )

        results = query.all()
        
        shops = []
        for shop in results:
            shop_data = shop.__dict__.copy()
            shop_data["owner_name"] = shop.owner.name if shop.owner else None
            shop_data["area_name"] = shop.area.name if shop.area else None
            shop_data["archived_by_name"] = shop.archived_by.name if getattr(shop, 'archived_by', None) else None
            shop_data.pop("_sa_instance_state", None)
            shop_data["assigned_users"] = [
                {"id": u.id, "name": u.name, "role": getattr(u.role, 'value', str(u.role)) if u.role else None} 
                for u in getattr(shop, 'assigned_owners_list', [])
            ]
            shops.append(shop_data)
        return shops

    # ── Unarchive ──
    @staticmethod
    def unarchive_shop(db: Session, shop_id: int, current_user: User):
        db_shop = ShopService.get_shop(db, shop_id)

        # Check permissions
        if current_user.role != "ADMIN":
            if db_shop.archived_by_id != current_user.id and not any(u.id == current_user.id for u in db_shop.assigned_owners_list):
                 raise HTTPException(status_code=403, detail="Not authorized to unarchive this shop")

        db_shop.is_archived = False
        db_shop.archived_by_id = None
        db.commit()
        db.refresh(db_shop)
        return db_shop

    # ── Hard Delete (Admin only) ──
    @staticmethod
    def hard_delete_shop(db: Session, shop_id: int):
        from sqlalchemy import or_
        db_shop = ShopService.get_shop(db, shop_id)
        
        conditions = []
        if db_shop.email:
            conditions.append(Client.email == db_shop.email)
        if db_shop.phone:
            conditions.append(Client.phone == db_shop.phone)
            
        if conditions:
            client_exists = db.query(Client).filter(or_(*conditions)).first()
            if client_exists:
                raise HTTPException(status_code=400, detail="Cannot delete shop that has been converted to a client")

        db.delete(db_shop)
        db.commit()
        return {"detail": "Shop permanently deleted"}
