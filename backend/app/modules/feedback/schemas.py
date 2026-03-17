# backend/app/modules/feedback/schemas.py
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class FeedbackBase(BaseModel):
    rating: int
    comments: Optional[str] = None
    client_name: Optional[str] = None
    mobile: Optional[str] = None
    shop_name: Optional[str] = None
    product: Optional[str] = None
    agent_name: Optional[str] = None
    agent_role: Optional[str] = None
    referral_code: Optional[str] = None
    client_id: Optional[int] = None

class FeedbackCreate(FeedbackBase):
    pass

class FeedbackRead(FeedbackBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserFeedbackBase(BaseModel):
    subject: str
    message: str

class UserFeedbackCreate(UserFeedbackBase):
    pass

class UserFeedbackUpdate(BaseModel):
    status: str

class UserFeedbackRead(UserFeedbackBase):
    id: int
    user_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
