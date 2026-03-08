from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class AreaBase(BaseModel):
    name: str
    description: Optional[str] = None
    pincode: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    radius_meters: Optional[int] = 500
    shop_limit: Optional[int] = 20
    priority_level: Optional[str] = "MEDIUM"
    auto_discovery_enabled: Optional[bool] = False
    target_categories: Optional[List[str]] = None

class AreaCreate(AreaBase):
    pass

class AreaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pincode: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    radius_meters: Optional[int] = None
    shop_limit: Optional[int] = None
    priority_level: Optional[str] = None
    auto_discovery_enabled: Optional[bool] = None
    target_categories: Optional[List[str]] = None

class AreaAssign(BaseModel):
    assigned_user_id: int
    shop_ids: Optional[List[int]] = None

class AreaRead(AreaBase):
    id: int
    assigned_user_id: Optional[int] = None
    shops_count: Optional[int] = 0
    
    model_config = ConfigDict(from_attributes=True)
