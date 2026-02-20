from typing import Optional
from pydantic import BaseModel, ConfigDict

class AreaBase(BaseModel):
    name: str
    pincode: Optional[str] = None
    city: Optional[str] = None

class AreaCreate(AreaBase):
    pass

class AreaAssign(BaseModel):
    assigned_user_id: int

class AreaRead(AreaBase):
    id: int
    assigned_user_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)
