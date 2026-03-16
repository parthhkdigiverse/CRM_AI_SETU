# backend/app/modules/areas/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean, Boolean, JSON, Table, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.mixins import SoftDeleteMixin

area_assignments = Table(
    "area_assignments",
    Base.metadata,
    Column("area_id", Integer, ForeignKey("areas.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)

class Area(SoftDeleteMixin, Base):
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
    is_deleted = Column(Boolean, default=False, index=True)
    
    assignment_status = Column(String, default="UNASSIGNED", nullable=False)
    
    # Lead Acceptance Tracking
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Advanced Targeting
    radius_meters = Column(Integer, default=500, nullable=False)
    shop_limit = Column(Integer, default=20, nullable=False)
    priority_level = Column(String, default="MEDIUM", nullable=False)
    auto_discovery_enabled = Column(Boolean, default=False, nullable=False)
    target_categories = Column(JSON, nullable=True)
    
    # Relationships
    assigned_user = relationship("app.modules.users.models.User", foreign_keys=[assigned_user_id], backref="assigned_areas")
    assigned_by = relationship("app.modules.users.models.User", foreign_keys=[assigned_by_id], backref="areas_assigned_out")
    creator = relationship("app.modules.users.models.User", foreign_keys=[created_by_id], backref="areas_created")
    assigned_users_list = relationship("app.modules.users.models.User", secondary=area_assignments, backref="assigned_areas_list")

