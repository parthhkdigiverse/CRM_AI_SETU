from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, index=True)
    organization = Column(String)
    referral_code = Column(String, nullable=True)
    referred_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    projects = relationship("app.modules.projects.models.Project", back_populates="client")
    referred_by = relationship("app.modules.users.models.User", backref="referred_clients")
