from beanie import Document
from typing import Optional, List, Any
from datetime import datetime

class Area(Document):
    name: str
    description: Optional[str] = None
    pincode: Optional[str] = None
    city: Optional[str] = None
    assigned_user_id: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_deleted: bool = False
    assignment_status: str = "UNASSIGNED"
    assigned_by_id: Optional[str] = None
    accepted_at: Optional[datetime] = None
    created_by_id: Optional[str] = None
    radius_meters: int = 500
    shop_limit: int = 20
    priority_level: str = "MEDIUM"
    auto_discovery_enabled: bool = False
    target_categories: Optional[List[Any]] = None
    assigned_user_ids: Optional[List[int]] = []

    class Settings:
        name = "areas"
