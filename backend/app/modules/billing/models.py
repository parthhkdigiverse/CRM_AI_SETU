from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True) # Populated after conversion
    amount = Column(Float, nullable=False)
    status = Column(String, default="PENDING") # PENDING, PAID, CANCELLED
    invoice_number = Column(String, unique=True, index=True)
    whatsapp_sent = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    shop = relationship("app.modules.shops.models.Shop", backref="bills")
    client = relationship("app.modules.clients.models.Client", backref="bills")
