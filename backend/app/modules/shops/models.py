# backend/app/modules/shops/models.py
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.core.database import Base
from app.core.mixins import SoftDeleteMixin


class ShopStatus(str, enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    MEETING_SET = "MEETING_SET"
    CONVERTED = "CONVERTED"

shop_assignments = Table(
    "shop_assignments",
    Base.metadata,
    Column("shop_id", Integer, ForeignKey("shops.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)

class Shop(SoftDeleteMixin, Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    address = Column(Text, nullable=True)
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    source = Column(String, default="Other")  # For lead sources donut chart

    # From master branch: additional lead/project fields
    project_type = Column(String, nullable=True)   # e.g., "AI Integration", "CRM Setup"
    requirements = Column(Text, nullable=True)
    status = Column(Enum(ShopStatus), default=ShopStatus.NEW, index=True)

    # Foreign keys — from both branches
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    
    assignment_status = Column(String, default="UNASSIGNED", nullable=False)
    
    # Lead Acceptance Tracking
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships — from both branches
    owner = relationship("app.modules.users.models.User", foreign_keys=[owner_id], backref="assigned_shops")
    assigned_by = relationship("app.modules.users.models.User", foreign_keys=[assigned_by_id], backref="shops_assigned_out")
    creator = relationship("app.modules.users.models.User", foreign_keys=[created_by_id], backref="shops_created")
    area = relationship("app.modules.areas.models.Area", backref="shops")
    assigned_owners_list = relationship("app.modules.users.models.User", secondary=shop_assignments, backref="assigned_shops_list")


# Explicit imports at end to avoid circular dependency issues
from app.modules.areas.models import Area
from app.modules.users.models import User
