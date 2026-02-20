import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class LeadStatus(str, enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    INTERESTED = "INTERESTED"
    CONVERTED = "CONVERTED"
    LOST = "LOST"

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    phone = Column(String, index=True, nullable=False)
    email = Column(String, nullable=True)
    company_name = Column(String, nullable=True) # Shop name
    address = Column(String, nullable=True)
    status = Column(Enum(LeadStatus), default=LeadStatus.NEW, index=True)
    
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True) # for future assignment
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("app.modules.users.models.User", backref="leads")
