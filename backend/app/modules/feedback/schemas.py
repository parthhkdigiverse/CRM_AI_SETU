from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class FeedbackBase(BaseModel):
    rating: int
    comments: Optional[str] = None
    client_name: Optional[str] = None
    client_id: Optional[int] = None

class FeedbackCreate(FeedbackBase):
    pass

class FeedbackRead(FeedbackBase):
    id: int
    client_id: int
    created_at: datetime

    class Config:
        from_attributes = True
