from typing import Optional
from pydantic import BaseModel, ConfigDict

class AreaBase(BaseModel):
    name: str
    description: Optional[str] = None
    pincode: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class AreaCreate(AreaBase):
    pass

class AreaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pincode: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class AreaAssign(BaseModel):
    assigned_user_id: int

class AreaRead(AreaBase):
    id: int
    assigned_user_id: Optional[int] = None
    shops_count: Optional[int] = 0
    
    model_config = ConfigDict(from_attributes=True)
