from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.modules.issues.models import IssueStatus, IssueSeverity

class IssueBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: IssueStatus = IssueStatus.PENDING
    severity: IssueSeverity = IssueSeverity.MEDIUM
    client_id: int
    project_id: Optional[int] = None
    reporter_id: Optional[int] = None
    remarks: Optional[str] = None
    opened_at: Optional[datetime] = None

class IssueCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: IssueStatus = IssueStatus.PENDING
    severity: IssueSeverity = IssueSeverity.MEDIUM
    project_id: Optional[int] = None
    remarks: Optional[str] = None

class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[IssueStatus] = None
    severity: Optional[IssueSeverity] = None
    remarks: Optional[str] = None

class IssueAssign(BaseModel):
    assigned_to_id: int

class IssueRead(IssueBase):
    id: int
    assigned_to_id: Optional[int] = None
    pm_name: Optional[str] = None
    project_name: Optional[str] = None
    created_at: Optional[datetime] = None
    reporter_name: Optional[str] = None

    class Config:
        from_attributes = True
