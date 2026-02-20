from typing import Optional
from pydantic import BaseModel
from app.modules.issues.models import IssueStatus

class IssueBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: IssueStatus = IssueStatus.OPEN
    project_id: int
    reporter_id: Optional[int] = None

class IssueCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: IssueStatus = IssueStatus.OPEN

class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[IssueStatus] = None

class IssueAssign(BaseModel):
    assigned_to_id: int

class IssueRead(IssueBase):
    id: int
    assigned_to_id: Optional[int] = None

    class Config:
        from_attributes = True
