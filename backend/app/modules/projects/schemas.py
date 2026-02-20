from typing import Optional
from pydantic import BaseModel

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    client_id: int
    pm_id: Optional[int] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    name: Optional[str] = None
    client_id: Optional[int] = None
    pm_id: Optional[int] = None

class ProjectAssign(BaseModel):
    pm_id: int

class ProjectRead(ProjectBase):
    id: int

    class Config:
        from_attributes = True

class ProjectMemberCreate(BaseModel):
    employee_id: int
    role: Optional[str] = None

class ProjectMemberRead(BaseModel):
    project_id: int
    employee_id: int
    employee_name: str
    role: Optional[str] = None

    class Config:
        from_attributes = True
