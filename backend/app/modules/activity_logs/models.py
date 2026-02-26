import enum
from sqlalchemy import Column, Integer, String, Enum, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class ActionType(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    ASSIGN = "ASSIGN"
    UNASSIGN = "UNASSIGN"
    STATUS_CHANGE = "STATUS_CHANGE"
    RESCHEDULE = "RESCHEDULE"
    CANCEL = "CANCEL"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"

class EntityType(str, enum.Enum):
    CLIENT = "CLIENT"
    PROJECT = "PROJECT"
    ISSUE = "ISSUE"
    MEETING = "MEETING"
    LEAD = "LEAD"
    REASSIGN = "REASSIGN"
    FEEDBACK = "FEEDBACK"
    USER = "USER"

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_role = Column(String, nullable=False) # Store current role as string for audit stability
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    
    old_data = Column(JSON, nullable=True)
    new_data = Column(JSON, nullable=True)
    
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("app.modules.users.models.User", backref="activity_logs")
