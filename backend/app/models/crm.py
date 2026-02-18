from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum
from datetime import datetime

class IssueStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String)
    organization = Column(String)
    
    projects = relationship("Project", back_populates="client")

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    pm_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    client = relationship("Client", back_populates="projects")
    pm = relationship("User", backref="managed_projects")
    issues = relationship("Issue", back_populates="project")
    meeting_summaries = relationship("MeetingSummary", back_populates="project")

class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text)
    status = Column(Enum(IssueStatus), default=IssueStatus.OPEN, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    project = relationship("Project", back_populates="issues")
    reporter = relationship("User", backref="reported_issues")

class MeetingSummary(Base):
    __tablename__ = "meeting_summaries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    project = relationship("Project", back_populates="meeting_summaries")
