import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class IssueStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"

class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text)
    status = Column(Enum(IssueStatus), default=IssueStatus.OPEN, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    project = relationship("app.modules.projects.models.Project", back_populates="issues")
    reporter = relationship("app.modules.users.models.User", foreign_keys=[reporter_id], backref="reported_issues")
    assigned_to = relationship("app.modules.users.models.User", foreign_keys=[assigned_to_id], backref="assigned_issues")
