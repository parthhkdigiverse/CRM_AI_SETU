from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Area(Base):
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    pincode = Column(String, index=True, nullable=True)
    city = Column(String, index=True, nullable=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    assigned_user = relationship("app.modules.users.models.User", backref="assigned_areas")
