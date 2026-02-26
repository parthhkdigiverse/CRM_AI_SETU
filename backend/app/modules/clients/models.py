from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

from app.core.database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, index=True)
    organization = Column(String)
    referral_code = Column(String, nullable=True)
    referred_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True) # For assignment
    pm_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Automatically assigned Project Manager
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    
    referred_by = relationship("app.modules.users.models.User", foreign_keys=[referred_by_id], backref="referred_clients")
    owner = relationship("app.modules.users.models.User", foreign_keys=[owner_id], backref="owned_clients")
    pm = relationship("app.modules.users.models.User", foreign_keys=[pm_id], backref="managed_clients")

class ClientPMHistory(Base):
    __tablename__ = "client_pm_history"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    pm_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=lambda: datetime.now(UTC))


    # Note: relationships can be added here if needed, but not strictly necessary for simple auditing.
