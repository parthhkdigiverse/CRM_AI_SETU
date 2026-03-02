from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.modules.projects.models import ProjectStatus

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    client_id: int
    pm_id: int
    status: Optional[ProjectStatus] = ProjectStatus.PLANNING
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = 0.0

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pm_id: Optional[int] = None
    status: Optional[ProjectStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None


class ProjectRead(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    # Progress metrics (calculated in service)
    total_issues: Optional[int] = 0
    resolved_issues: Optional[int] = 0
    progress_percentage: Optional[float] = 0.0

    model_config = ConfigDict(from_attributes=True)

