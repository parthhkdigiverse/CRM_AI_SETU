from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request
from app.modules.leads.models import Lead, LeadStatus
from app.modules.leads.schemas import LeadCreate, LeadUpdate
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from datetime import datetime

class LeadService:
    def __init__(self, db: Session):
        self.db = db
        self.activity_logger = ActivityLogger(db)

    def get_lead(self, lead_id: int):
        return self.db.query(Lead).filter(Lead.id == lead_id).first()

    def get_leads(self, skip: int = 0, limit: int = 100, owner_id: int = None):
        query = self.db.query(Lead)
        if owner_id:
            query = query.filter(Lead.owner_id == owner_id)
        return query.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()

    async def create_lead(self, lead_in: LeadCreate, current_user: User, request: Request):
        lead = Lead(**lead_in.model_dump(), owner_id=current_user.id)
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)

        # Log Activity
        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.CREATE,
            entity_type=EntityType.LEAD, # Need to add LEAD to EntityType enum
            entity_id=lead.id,
            new_data=lead_in.model_dump(),
            request=request
        )
        return lead

    async def update_lead(self, lead_id: int, lead_in: LeadUpdate, current_user: User, request: Request):
        lead = self.get_lead(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        old_data = {
            "name": lead.name,
            "status": lead.status.value,
            "phone": lead.phone
        }

        update_data = lead_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(lead, field, value)

        self.db.commit()
        self.db.refresh(lead)

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.UPDATE,
            entity_type=EntityType.LEAD,
            entity_id=lead.id,
            old_data=old_data,
            new_data=update_data,
            request=request
        )
        return lead

    async def convert_lead(self, lead_id: int, current_user: User, request: Request):
        lead = self.get_lead(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # 1. Double Conversion Prevention
        if lead.status == LeadStatus.CONVERTED:
            raise HTTPException(status_code=400, detail="Lead is already converted")
        
        existing_client = self.db.query(Client).filter(Client.lead_id == lead_id).first()
        if existing_client:
            raise HTTPException(status_code=400, detail="Client already exists for this lead")

        # 2. Create Client
        new_client = Client(
            name=lead.name,
            phone=lead.phone,
            email=lead.email if lead.email else f"lead_{lead.id}@placeholder.com", # Email is required for Client, unique
            organization=lead.company_name,
            lead_id=lead.id,
            referred_by_id=current_user.id, # The person converting gets the referral credit? Or the original owner? 
                                            # "Assign area to user" implies sales. Let's say converter is the referrer.
            created_at=datetime.utcnow()
        )
        self.db.add(new_client)
        
        # 3. Update Lead Status
        lead.status = LeadStatus.CONVERTED
        
        self.db.commit()
        self.db.refresh(new_client)

        # 4. Log Activity
        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.STATUS_CHANGE,
            entity_type=EntityType.LEAD,
            entity_id=lead.id,
            old_data={"status": "NEW"}, # Simplified old data
            new_data={"status": "CONVERTED", "client_id": new_client.id},
            request=request
        )

        return new_client
