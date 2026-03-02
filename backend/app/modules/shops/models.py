from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    address = Column(Text, nullable=True)
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    source = Column(String, default="Other") # For lead sources donut chart
    created_at = Column(DateTime, default=datetime.utcnow)
    # Add the foreign key linking to the Area table
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)

    # Establish the ORM relationship for easy querying later
    area = relationship("Area", backref="shops")
