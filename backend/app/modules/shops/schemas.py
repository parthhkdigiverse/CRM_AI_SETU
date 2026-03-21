# backend/app/modules/shops/schemas.py
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from app.core.enums import MasterPipelineStage


class ShopBase(BaseModel):
    name: str
    address: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    source: Optional[str] = "Other"
    project_type: Optional[str] = None
    requirements: Optional[str] = None
    area_id: Optional[int] = None
    pipeline_stage: Optional[MasterPipelineStage] = MasterPipelineStage.LEAD
    owner_id: Optional[int] = None


class ShopCreate(ShopBase):
    pass


class ShopUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    source: Optional[str] = None
    project_type: Optional[str] = None
    requirements: Optional[str] = None
    area_id: Optional[int] = None
    pipeline_stage: Optional[MasterPipelineStage] = None
    owner_id: Optional[int] = None
    project_manager_id: Optional[int] = None
    demo_stage: Optional[int] = None
    demo_scheduled_at: Optional[datetime] = None


class AssignPMRequest(BaseModel):
    pm_id: int
    demo_scheduled_at: Optional[datetime] = None


class AssignedUser(BaseModel):
    id: int
    name: Optional[str] = None
    role: Optional[str] = None


class ShopRead(ShopBase):
    id: int
    owner_name: Optional[str] = None
    area_name: Optional[str] = None
    created_at: datetime
    is_archived: Optional[bool] = False
    archived_by_id: Optional[int] = None
    archived_by_name: Optional[str] = None
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    assignment_status: Optional[str] = "UNASSIGNED"
    assigned_users: list[AssignedUser] = []
    last_visitor_name: Optional[str] = None
    last_visit_status: Optional[str] = None
    project_manager_id: Optional[int] = None
    project_manager_name: Optional[str] = None
    demo_stage: Optional[int] = 0
    demo_scheduled_at: Optional[datetime] = None
    demo_title: Optional[str] = None
    demo_type: Optional[str] = None
    demo_notes: Optional[str] = None
    demo_meet_link: Optional[str] = None

    class Config:
        from_attributes = True
