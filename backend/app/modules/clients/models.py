from beanie import Document
from typing import Optional
from datetime import datetime, timezone

class Client(Document):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None
    address: Optional[str] = None
    project_type: Optional[str] = None
    requirements: Optional[str] = None
    referral_code: Optional[str] = None
    referred_by_id: Optional[str] = None
    owner_id: Optional[str] = None
    pm_id: Optional[str] = None
    is_active: bool = True
    is_deleted: bool = False
    created_at: datetime = datetime.now(timezone.utc)

    class Settings:
        name = "clients"

class ClientPMHistory(Document):
    client_id: str
    pm_id: str
    assigned_at: datetime = datetime.now(timezone.utc)

    class Settings:
        name = "client_pm_history"
