# backend/app/modules/visits/models.py
import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

from app.core.database import Base

class VisitStatus(str, enum.Enum):
    SATISFIED          = "SATISFIED"
    ACCEPT             = "ACCEPT"
    DECLINE            = "DECLINE"
    MISSED             = "MISSED"
    TAKE_TIME_TO_THINK = "TAKE_TIME_TO_THINK"
    OTHER              = "OTHER"
    COMPLETED          = "COMPLETED"
    CANCELLED          = "CANCELLED"
    SCHEDULED          = "SCHEDULED"

class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    status = Column(Enum(VisitStatus), default=VisitStatus.SATISFIED)
    remarks = Column(Text, nullable=True)
    decline_remarks = Column(Text, nullable=True)
    visit_date = Column(DateTime, default=lambda: datetime.now(UTC))
    
    # Photo persistence
    photo_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    is_deleted = Column(Boolean, default=False)

    shop = relationship("app.modules.shops.models.Shop", backref="visits")
    user = relationship("app.modules.users.models.User", backref="visits")

    @property
    def shop_name(self) -> str:
        return self.shop.name if self.shop else None
        
    @property
    def user_name(self) -> str:
        return self.user.name if self.user else None

    @property
    def area_name(self) -> str:
        return self.shop.area.name if self.shop and self.shop.area else None

    @property
    def project_manager_name(self) -> str:
        return self.shop.project_manager.name if self.shop and getattr(self.shop, 'project_manager', None) else None

    @property
    def shop_status(self) -> str:
        return self.shop.status.value if self.shop and self.shop.status else None

    @property
    def shop_demo_stage(self) -> int:
        return getattr(self.shop, 'demo_stage', 0) if self.shop else 0

