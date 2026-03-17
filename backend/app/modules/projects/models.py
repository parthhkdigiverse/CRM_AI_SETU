# backend/app/modules/projects/models.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.enums import GlobalTaskStatus


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    pm_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    status = Column(Enum(GlobalTaskStatus), default=GlobalTaskStatus.OPEN)

    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    budget = Column(Float, default=0.0)
    is_deleted = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("app.modules.clients.models.Client", backref="projects")
    project_manager = relationship("app.modules.users.models.User", backref="projects")
