from beanie import PydanticObjectId
# backend/app/modules/issues/schemas.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.core.enums import GlobalTaskStatus
from app.modules.issues.models import IssueSeverity


class IssueBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: GlobalTaskStatus = GlobalTaskStatus.OPEN
    severity: IssueSeverity = IssueSeverity.MEDIUM
    client_id: str
    project_id: Optional[str] = None
    reporter_id: Optional[str] = None
    remarks: Optional[str] = None
    opened_at: Optional[datetime] = None


class IssueCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: GlobalTaskStatus = GlobalTaskStatus.OPEN
    severity: IssueSeverity = IssueSeverity.MEDIUM
    project_id: Optional[str] = None
    assigned_to_id: Optional[str] = None
    remarks: Optional[str] = None


class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[GlobalTaskStatus] = None
    severity: Optional[IssueSeverity] = None
    remarks: Optional[str] = None


class IssueAssign(BaseModel):
    assigned_to_id: str


class IssueRead(IssueBase):
    id: Optional[PydanticObjectId] = None
    assigned_to_id: Optional[str] = None
    pm_name: Optional[str] = None
    project_name: Optional[str] = None
    created_at: Optional[datetime] = None
    reporter_name: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True
