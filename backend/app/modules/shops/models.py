import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.core.database import Base

class ShopStatus(str, enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    MEETING_SET = "MEETING_SET"
    CONVERTED = "CONVERTED"

class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    address = Column(Text, nullable=True)
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    source = Column(String, default="Other") # For lead sources donut chart
    
    project_type = Column(String, nullable=True) # e.g., "AI Integration", "CRM Setup"
    requirements = Column(Text, nullable=True)
    
    status = Column(Enum(ShopStatus), default=ShopStatus.NEW, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    owner = relationship("app.modules.users.models.User", backref="assigned_shops")
    area = relationship("app.modules.areas.models.Area", backref="shops")
