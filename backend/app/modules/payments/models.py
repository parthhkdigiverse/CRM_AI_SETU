import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    amount = Column(Float, nullable=False)
    qr_code_data = Column(String, nullable=True) # Could store URL or text
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    generated_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)

    client = relationship("app.modules.clients.models.Client", backref="payments")
    generated_by = relationship("app.modules.users.models.User", foreign_keys=[generated_by_id])
    verified_by = relationship("app.modules.users.models.User", foreign_keys=[verified_by_id])
