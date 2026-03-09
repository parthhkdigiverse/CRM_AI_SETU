from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean, JSON, Table
from sqlalchemy.orm import relationship
from app.core.database import Base

area_assignments = Table(
    "area_assignments",
    Base.metadata,
    Column("area_id", Integer, ForeignKey("areas.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)

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
    
    # Advanced Targeting
    radius_meters = Column(Integer, default=500, nullable=False)
    shop_limit = Column(Integer, default=20, nullable=False)
    priority_level = Column(String, default="MEDIUM", nullable=False)
    auto_discovery_enabled = Column(Boolean, default=False, nullable=False)
    target_categories = Column(JSON, nullable=True)
    
    # Relationships
    assigned_user = relationship("app.modules.users.models.User", backref="assigned_areas")
    assigned_users_list = relationship("app.modules.users.models.User", secondary=area_assignments, backref="assigned_areas_list")

