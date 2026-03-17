# backend/app/modules/shops/models.py
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.core.database import Base
from app.core.enums import MasterPipelineStage

shop_assignments = Table(
    "shop_assignments",
    Base.metadata,
    Column("shop_id", Integer, ForeignKey("shops.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)

class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    address = Column(Text, nullable=True)
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    source = Column(String, default="Other")

    # Additional lead/project fields
    project_type = Column(String, nullable=True)
    requirements = Column(Text, nullable=True)
    pipeline_stage = Column(Enum(MasterPipelineStage), default=MasterPipelineStage.LEAD, index=True)
    is_deleted = Column(Boolean, default=False, index=True)

    # Foreign keys
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    assignment_status = Column(String, default="UNASSIGNED", nullable=False)

    # Lead Acceptance Tracking
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # PM Demo Pipeline
    project_manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    demo_stage = Column(Integer, default=0, nullable=False, server_default="0")
    demo_scheduled_at = Column(DateTime(timezone=True), nullable=True)
    demo_title = Column(String, nullable=True)
    demo_type = Column(String, nullable=True)
    demo_notes = Column(Text, nullable=True)
    demo_meet_link = Column(String, nullable=True)

    # Relationships
    owner = relationship("app.modules.users.models.User", foreign_keys=[owner_id], backref="assigned_shops")
    assigned_by = relationship("app.modules.users.models.User", foreign_keys=[assigned_by_id], backref="shops_assigned_out")
    creator = relationship("app.modules.users.models.User", foreign_keys=[created_by_id], backref="shops_created")
    area = relationship("app.modules.areas.models.Area", backref="shops")
    assigned_owners_list = relationship("app.modules.users.models.User", secondary=shop_assignments, backref="assigned_shops_list")
    project_manager = relationship("app.modules.users.models.User", foreign_keys=[project_manager_id], backref="pm_shops")

    @property
    def last_visitor_name(self):
        """Name of the user who logged the most recent visit."""
        if not self.visits:
            return None
        latest = max(self.visits, key=lambda v: v.visit_date or v.created_at)
        return latest.user.name if latest.user else None

    # Back-compat alias so any code still using .status doesn't hard-crash
    @property
    def status(self):
        return self.pipeline_stage

    @status.setter
    def status(self, value):
        self.pipeline_stage = value


# Explicit imports at end to avoid circular dependency issues
from app.modules.areas.models import Area
from app.modules.users.models import User
