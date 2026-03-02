import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class IssueStatus(str, enum.Enum):
    PENDING = "PENDING"
    SOLVED = "SOLVED"
    RESOLVED = "RESOLVED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCEL"

class IssueSeverity(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text)
    status = Column(String, default=IssueStatus.PENDING, nullable=False)
    severity = Column(String, default=IssueSeverity.MEDIUM, nullable=False)
    remarks = Column(Text, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    client = relationship("Client", backref="issues")
    project = relationship("Project", backref="issues")
    reporter = relationship("User", foreign_keys=[reporter_id], backref="reported_issues")

    assigned_to = relationship("User", foreign_keys=[assigned_to_id], backref="assigned_issues")

# Import models at the end to ensure they are registered without circular dependency issues
from app.modules.clients.models import Client
from app.modules.projects.models import Project
from app.modules.users.models import User
