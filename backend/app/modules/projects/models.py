import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Table, Enum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class ProjectStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    ONGOING = "ONGOING"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

project_members = Table(
    "project_members",
    Base.metadata,
    Column("project_id", Integer, ForeignKey("projects.id"), primary_key=True),
    Column("employee_id", Integer, ForeignKey("employees.id"), primary_key=True),
    Column("role", String, nullable=True)
)

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.PLANNED, index=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    pm_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("app.modules.clients.models.Client", back_populates="projects")
    pm = relationship("app.modules.users.models.User", backref="managed_projects")
    issues = relationship("app.modules.issues.models.Issue", back_populates="project")
    meeting_summaries = relationship("app.modules.meetings.models.MeetingSummary", back_populates="project")
    
    members = relationship("app.modules.employees.models.Employee", secondary=project_members, backref="projects")
