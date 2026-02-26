from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    client_name = Column(String, nullable=True) # For anonymous/external
    rating = Column(Integer, nullable=False)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("app.modules.clients.models.Client", backref="feedbacks")


class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("app.modules.users.models.User", backref="system_feedbacks")
