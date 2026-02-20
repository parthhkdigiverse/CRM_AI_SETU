from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True) # Optional if anonymous
    client_name = Column(String, nullable=True) # For anonymous/external
    rating = Column(Integer, nullable=False)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("app.modules.projects.models.Project", backref="feedbacks")
    client = relationship("app.modules.clients.models.Client", backref="feedbacks")
