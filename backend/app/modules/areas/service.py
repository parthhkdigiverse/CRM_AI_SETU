from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.modules.areas.models import Area
from app.modules.areas.schemas import AreaCreate
from app.modules.users.models import User

class AreaService:
    def __init__(self, db: Session):
        self.db = db

    def get_areas(self, skip: int = 0, limit: int = 100):
        return self.db.query(Area).offset(skip).limit(limit).all()

    def create_area(self, area_in: AreaCreate):
        area = Area(**area_in.model_dump())
        self.db.add(area)
        self.db.commit()
        self.db.refresh(area)
        return area

    def assign_area(self, area_id: int, user_id: int):
        area = self.db.query(Area).filter(Area.id == area_id).first()
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        area.assigned_user_id = user_id
        self.db.commit()
        self.db.refresh(area)
        return area
