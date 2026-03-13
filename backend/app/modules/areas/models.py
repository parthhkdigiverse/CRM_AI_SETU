from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class Area(Base):
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    pincode = Column(String, index=True, nullable=True)
    city = Column(String, index=True, nullable=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Add Google Maps coordinates
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    is_deleted = Column(Boolean, default=False, index=True)
    assigned_user = relationship("app.modules.users.models.User", backref="assigned_areas")
