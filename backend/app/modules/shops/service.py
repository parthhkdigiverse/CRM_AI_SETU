from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.modules.shops.models import Shop
from app.modules.shops.schemas import ShopCreate, ShopUpdate

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
    def list_shops(db: Session, skip: int = 0, limit: int = 100):
        return db.query(Shop).offset(skip).limit(limit).all()

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
    def delete_shop(db: Session, shop_id: int):
        from app.modules.clients.models import Client
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
