# backend/app/modules/feedback/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    client_name = Column(String, nullable=True) # Full Name
    mobile = Column(String, nullable=True)
    shop_name = Column(String, nullable=True)
    product = Column(String, nullable=True)
    rating = Column(Integer, nullable=False) # Sales Person Rating
    comments = Column(Text, nullable=True)
    agent_name = Column(String, nullable=True)
    referral_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)

    client = relationship("app.modules.clients.models.Client", backref="feedbacks")


class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)

    # Relationships
    user = relationship("app.modules.users.models.User", backref="system_feedbacks")
