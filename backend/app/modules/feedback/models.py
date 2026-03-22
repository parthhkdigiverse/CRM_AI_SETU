from beanie import Document
from typing import Optional
from datetime import datetime, timezone

class Feedback(Document):
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    mobile: Optional[str] = None
    shop_name: Optional[str] = None
    product: Optional[str] = None
    rating: int
    comments: Optional[str] = None
    agent_name: Optional[str] = None
    referral_code: Optional[str] = None
    created_at: datetime = datetime.now(timezone.utc)
    is_deleted: bool = False

    class Settings:
        name = "feedbacks"

class UserFeedback(Document):
    user_id: str
    subject: str
    message: str
    status: str = "PENDING"
    created_at: datetime = datetime.now(timezone.utc)
    is_deleted: bool = False

    class Settings:
        name = "user_feedbacks"
