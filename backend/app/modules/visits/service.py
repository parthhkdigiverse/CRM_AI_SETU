# backend/app/modules/visits/service.py
import os
import shutil
from pathlib import Path
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, UploadFile, Request
from datetime import date as dt_date, datetime, UTC, time, timedelta

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
        return self.db.query(Visit).filter(Visit.id == visit_id, Visit.is_deleted == False).first()

    def get_visits(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        current_user: User = None, 
        shop_id: int = None, 
        user_id: int | None = None,
        area_id: int | None = None,
        status: str | None = None,
        start_date: dt_date | None = None,
        end_date: dt_date | None = None
    ):
        try:
            from app.modules.shops.models import Shop as ShopModel
            from sqlalchemy import or_
            from app.modules.users.models import UserRole

            query = self.db.query(Visit).outerjoin(ShopModel, ShopModel.id == Visit.shop_id).options(
                joinedload(Visit.shop).joinedload(ShopModel.area),
                joinedload(Visit.shop).joinedload(ShopModel.project_manager),
                joinedload(Visit.user)
            ).filter(Visit.is_deleted == False)
            
            if shop_id:
                query = query.filter(Visit.shop_id == shop_id)
                # CRITICAL OVERRIDE: If a specific shop is requested, force the backend 
                # to ignore the router's hardcoded user_id filter so we can show all team visits.
                if current_user and current_user.role not in [UserRole.ADMIN]:
                    user_id = None 
            
            if user_id is not None:
                query = query.filter(Visit.user_id == user_id)
            if area_id is not None and str(area_id).upper() != "ALL":
                query = query.filter(ShopModel.area_id == area_id)
            if status is not None and status.upper() != "ALL":
                query = query.filter(Visit.status == status.upper())
            if start_date is not None:
                query = query.filter(Visit.visit_date >= start_date)
            if end_date is not None:
                query = query.filter(Visit.visit_date < (end_date + timedelta(days=1)))

            # --- SECURITY ENFORCEMENT ---
            if current_user and current_user.role not in [UserRole.ADMIN]:
                if not shop_id:
                    # Strict fallback for global lists
                    try:
                        query = query.filter(
                            or_(
                                Visit.user_id == current_user.id,
                                ShopModel.owner_id == current_user.id,
                                ShopModel.assigned_owners_list.any(id=current_user.id)
                            )
                        )
                    except Exception:
                        query = query.filter(
                            or_(
                                Visit.user_id == current_user.id,
                                ShopModel.owner_id == current_user.id
                            )
                        )

            return query.order_by(Visit.visit_date.desc()).offset(skip).limit(limit).all()
        except Exception as e:
            print(f"Error fetching visits: {e}")
            return []

    async def create_visit(self, visit_in: VisitCreate, current_user: User, request: Request, storefront_photo: UploadFile = None, selfie_photo: UploadFile = None):
        # Validation: Check Shop Exists
        shop = self.db.query(Shop).filter(Shop.id == visit_in.shop_id).first()
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")
            
        visit_data = visit_in.model_dump()

        visit = Visit(**visit_data, user_id=current_user.id)

        # Handle Photo Uploads
        timestamp = int(datetime.now(UTC).timestamp())
        
        if storefront_photo:
            try:
                file_ext = storefront_photo.filename.split(".")[-1]
                filename = f"visit_{visit_in.shop_id}_{current_user.id}_storefront_{timestamp}.{file_ext}"
                file_path = UPLOAD_DIR / filename
                with file_path.open("wb") as buffer:
                    shutil.copyfileobj(storefront_photo.file, buffer)
                visit.storefront_photo_url = f"/static/uploads/visits/{filename}"
                visit.photo_url = visit.storefront_photo_url # Backwards compatibility
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to upload storefront photo: {str(e)}")

        if selfie_photo:
            try:
                file_ext = selfie_photo.filename.split(".")[-1]
                filename = f"visit_{visit_in.shop_id}_{current_user.id}_selfie_{timestamp}.{file_ext}"
                file_path = UPLOAD_DIR / filename
                with file_path.open("wb") as buffer:
                    shutil.copyfileobj(selfie_photo.file, buffer)
                visit.selfie_photo_url = f"/static/uploads/visits/{filename}"
                if not visit.photo_url:
                    visit.photo_url = visit.selfie_photo_url # Backwards compatibility if only selfie provided
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to upload selfie photo: {str(e)}")

        self.db.add(visit)
        self.db.commit()

        # Re-fetch with eager-loaded relationships so @property fields
        # (shop_name, area_name, user_name) resolve during response serialization
        from app.modules.shops.models import Shop as ShopModel
        visit = (
            self.db.query(Visit)
            .options(
                joinedload(Visit.shop).joinedload(ShopModel.area),
                joinedload(Visit.user)
            )
            .filter(Visit.id == visit.id)
            .first()
        )

        # --- Auto-transition Shop pipeline_stage (Bulletproof Version) ---
        from app.core.enums import MasterPipelineStage
        shop = self.db.query(Shop).filter(Shop.id == visit_in.shop_id).first()

        if shop:
            # 1. Safely extract the visit status string
            v_status = visit.status.name if hasattr(visit.status, 'name') else str(visit.status).replace('VisitStatus.', '')

            # 2. Prevent the NULL Trap (Treat None as LEAD)
            current_stage = shop.pipeline_stage
            if current_stage is None:
                current_stage = MasterPipelineStage.LEAD

            c_stage_str = current_stage.name if hasattr(current_stage, 'name') else str(current_stage).replace('MasterPipelineStage.', '')

            # 3. State Machine using safe string comparisons, assigning proper Enum objects
            if v_status == "ACCEPT":
                shop.pipeline_stage = MasterPipelineStage.DELIVERY
            elif v_status in ["SATISFIED", "TAKE_TIME_TO_THINK", "OTHER"]:
                if c_stage_str == "LEAD":
                    shop.pipeline_stage = MasterPipelineStage.PITCHING
            elif v_status == "DECLINE":
                shop.is_deleted = True
                shop.assignment_status = "UNASSIGNED"

            self.db.commit()
            self.db.refresh(shop)
        # ----------------------------------------------------------

        # Helper for activity logging
        
        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.CREATE,
            entity_type=EntityType.VISIT,
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
            entity_type=EntityType.VISIT,
            entity_id=visit.id,
            old_data=old_data,
            new_data=update_data,
            request=request
        )
        return visit
