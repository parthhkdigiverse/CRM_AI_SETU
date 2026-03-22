from beanie import PydanticObjectId
# backend/app/modules/projects/schemas.py
from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.core.enums import GlobalTaskStatus


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    client_id: str
    pm_id: str
    status: Optional[GlobalTaskStatus] = GlobalTaskStatus.OPEN
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = 0.0


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pm_id: Optional[str] = None
    status: Optional[GlobalTaskStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None


class ProjectRead(ProjectBase):
    id: Optional[PydanticObjectId] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Extra names and contact info for UI
    client_name: Optional[str] = None
    pm_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    project_type: Optional[str] = None

    # Progress metrics (calculated in service)
    total_issues: Optional[int] = 0
    resolved_issues: Optional[int] = 0
    progress_percentage: Optional[float] = 0.0

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
