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
        return shop

    @staticmethod
    def list_shops(db: Session, skip: int = 0, limit: int = 100, status: ShopStatus = None, owner_id: int = None):
        from app.modules.areas.models import Area
        query = db.query(
            Shop, 
            User.name.label("owner_name"),
            Area.name.label("area_name")
        ).outerjoin(User, Shop.owner_id == User.id).outerjoin(Area, Shop.area_id == Area.id)
        
        if status:
            query = query.filter(Shop.status == status)
        if owner_id:
            query = query.filter(Shop.owner_id == owner_id)
        
        results = query.offset(skip).limit(limit).all()
        shops = []
        for shop, owner_name, area_name in results:
            shop_data = shop.__dict__.copy()
            shop_data["owner_name"] = owner_name
            shop_data["area_name"] = area_name
            shops.append(shop_data)
        return shops
        
    @staticmethod
    def list_kanban_shops(db: Session, owner_id: int = None):
        from app.modules.areas.models import Area
        query = db.query(
            Shop, 
            User.name.label("owner_name"),
            Area.name.label("area_name")
        ).outerjoin(User, Shop.owner_id == User.id).outerjoin(Area, Shop.area_id == Area.id)
        
        if owner_id:
            query = query.filter(Shop.owner_id == owner_id)
            
        results = query.all()
        
        kanban = {
            "NEW": [],
            "CONTACTED": [],
            "MEETING_SET": [],
            "CONVERTED": [],
        }
        
        for shop, owner_name, area_name in results:
            shop_data = shop.__dict__.copy()
            shop_data["owner_name"] = owner_name
            shop_data["area_name"] = area_name
            # Ensure status is string for key lookup
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
    def convert_lead_to_client(db: Session, shop_id: int):
        db_shop = ShopService.get_shop(db, shop_id)
        
        if db_shop.status == ShopStatus.CONVERTED:
            raise HTTPException(status_code=400, detail="Lead already converted to client")
            
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

    @staticmethod
    def delete_shop(db: Session, shop_id: int):
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
        return {"detail": "Shop deleted successfully"}
