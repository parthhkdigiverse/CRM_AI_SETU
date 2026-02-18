from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.models.crm import IssueStatus

# Client Schemas
class ClientBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    organization: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(ClientBase):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

class ClientRead(ClientBase):
    id: int

    class Config:
        from_attributes = True

# Project Schemas
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    client_id: int
    pm_id: int

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    name: Optional[str] = None
    client_id: Optional[int] = None
    pm_id: Optional[int] = None

class ProjectRead(ProjectBase):
    id: int

    class Config:
        from_attributes = True

# Issue Schemas
class IssueBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: IssueStatus = IssueStatus.OPEN
    project_id: int
    reporter_id: int

class IssueCreate(IssueBase):
    pass

class IssueUpdate(IssueBase):
    title: Optional[str] = None
    status: Optional[IssueStatus] = None

class IssueRead(IssueBase):
    id: int

    class Config:
        from_attributes = True

# Meeting Summary Schemas
class MeetingSummaryBase(BaseModel):
    title: str
    content: str
    date: Optional[datetime] = None
    project_id: int

class MeetingSummaryCreate(MeetingSummaryBase):
    pass

class MeetingSummaryRead(MeetingSummaryBase):
    id: int

    class Config:
        from_attributes = True
