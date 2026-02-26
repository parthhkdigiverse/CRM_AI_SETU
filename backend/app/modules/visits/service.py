import os
import shutil
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile, Request
from datetime import datetime, UTC

from app.modules.visits.models import Visit, VisitStatus
from app.modules.visits.schemas import VisitCreate, VisitUpdate
from app.modules.users.models import User
from app.modules.shops.models import Shop
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType

BASE_DIR = Path(__file__).parent.parent.parent.parent # points to backend/
UPLOAD_DIR = BASE_DIR / "static" / "uploads" / "visits"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class VisitService:
    def __init__(self, db: Session):
        self.db = db
        self.activity_logger = ActivityLogger(db)

    def get_visit(self, visit_id: int):
        return self.db.query(Visit).filter(Visit.id == visit_id).first()

    def get_visits(self, skip: int = 0, limit: int = 100, user_id: int = None, shop_id: int = None):
        query = self.db.query(Visit)
        if user_id:
            query = query.filter(Visit.user_id == user_id)
        if shop_id:
            query = query.filter(Visit.shop_id == shop_id)
        return query.order_by(Visit.visit_date.desc()).offset(skip).limit(limit).all()

    async def create_visit(self, visit_in: VisitCreate, current_user: User, request: Request, photo: UploadFile = None):
        # Validation: Check Shop Exists
        shop = self.db.query(Shop).filter(Shop.id == visit_in.shop_id).first()
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")
            
        visit_data = visit_in.model_dump()
        
        # Validation: Duplicate Visit Protection (One per user, per lead, per day)
        target_date = visit_data.get('visit_date') or datetime.now(UTC)

        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        existing_visit = self.db.query(Visit).filter(
            Visit.shop_id == visit_in.shop_id,
            Visit.user_id == current_user.id,
            Visit.visit_date >= start_of_day,
            Visit.visit_date <= end_of_day
        ).first()
        
        if existing_visit:
            raise HTTPException(status_code=400, detail="A visit has already been logged for this shop today by the current user.")

        visit = Visit(**visit_data, user_id=current_user.id)

        # Handle Photo Upload
        if photo:
            try:
                # Validate file extension if needed, for now accept images
                file_ext = photo.filename.split(".")[-1]
                filename = f"visit_{visit_in.shop_id}_{current_user.id}_{int(datetime.now(UTC).timestamp())}.{file_ext}"

                file_path = UPLOAD_DIR / filename
                
                with file_path.open("wb") as buffer:
                    shutil.copyfileobj(photo.file, buffer)
                
                # Store relative path or URL
                visit.photo_url = f"/static/uploads/visits/{filename}"
            except Exception as e:
                # Log error but maybe don't fail the visit creation? 
                # Requirement: "file is actually written... invalid/missing rejected"
                # If upload fails, we should probably fail the request or mark it.
                raise HTTPException(status_code=500, detail=f"Failed to upload photo: {str(e)}")

        self.db.add(visit)
        self.db.commit()
        self.db.refresh(visit)
        
        # Helper for activity logging
        
        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.CREATE,
            entity_type=EntityType.LEAD,
            entity_id=visit.id,
            new_data=visit_in.model_dump(mode='json'), # mode='json' for dates
            request=request
        )
        
        return visit

    async def update_visit(self, visit_id: int, visit_in: VisitUpdate, current_user: User, request: Request):
        visit = self.get_visit(visit_id)
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")

        old_data = {
            "status": visit.status.value,
            "remarks": visit.remarks
        }
        
        update_data = visit_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(visit, field, value)

        self.db.commit()
        self.db.refresh(visit)

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.UPDATE,
            entity_type=EntityType.LEAD,
            entity_id=visit.id,
            old_data=old_data,
            new_data=update_data,
            request=request
        )
        return visit
