# backend/app/modules/settings/models.py
from sqlalchemy import Column, Integer, JSON
from app.core.database import Base

class SystemSettings(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    feature_flags = Column(JSON, nullable=False, default=dict)
