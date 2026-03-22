# backend/app/modules/shops/models.py
import enum
from datetime import datetime, UTC
from typing import Optional, List, Annotated  # Annotated add karyu chhe
from beanie import Document, Indexed
from pydantic import Field
from app.core.enums import MasterPipelineStage

class Shop(Document):
    # name: Indexed(str) ni yellow line solve karva mate Annotated vapryu chhe
    name: Annotated[str, Indexed()] 
    address: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    source: str = "Other"

    # Additional lead/project fields
    project_type: Optional[str] = None
    requirements: Optional[str] = None
    pipeline_stage: MasterPipelineStage = MasterPipelineStage.LEAD
    is_deleted: bool = False

    # Foreign keys
    owner_id: Optional[str] = None
    area_id: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    assignment_status: str = "UNASSIGNED"

    # Lead Acceptance Tracking
    assigned_by_id: Optional[str] = None
    accepted_at: Optional[datetime] = None
    created_by_id: Optional[str] = None

    # PM Demo Pipeline
    project_manager_id: Optional[str] = None
    demo_stage: int = 0
    demo_scheduled_at: Optional[datetime] = None
    demo_title: Optional[str] = None
    demo_type: Optional[str] = None
    demo_notes: Optional[str] = None
    demo_meet_link: Optional[str] = None

    # Many-to-Many mate simple list
    assigned_owners_list: List[str] = []

    class Settings:
        name = "shops"

    @property
    def status(self):
        return self.pipeline_stage

    @status.setter
    def status(self, value):
        self.pipeline_stage = value

# Circular dependency mate imports
from app.modules.areas.models import Area
from app.modules.users.models import User