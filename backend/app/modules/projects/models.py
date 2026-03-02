from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, Float

from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base

class ProjectStatus(str, enum.Enum):
    PLANNING = "PLANNING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"
    CANCELLED = "CANCELLED"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    pm_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    status = Column(Enum(ProjectStatus), default=ProjectStatus.PLANNING)
    
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    budget = Column(Float, default=0.0)

    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("app.modules.clients.models.Client", backref="projects")
    project_manager = relationship("app.modules.users.models.User", backref="projects")
