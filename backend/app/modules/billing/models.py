# backend/app/modules/billing/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.core.database import Base


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)

    # Optional shop linkage (pre-existing lead)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=True)
    # Linked client (populated after invoice is sent/verified)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)

    # Client detail snapshot (collected before invoice is created)
    invoice_client_name = Column(String, nullable=False)
    invoice_client_phone = Column(String, nullable=False)
    invoice_client_email = Column(String, nullable=True)
    invoice_client_address = Column(Text, nullable=True)
    invoice_client_org = Column(String, nullable=True)

    # Financial
    amount = Column(Float, nullable=False, default=12000.0)
    payment_type = Column(String, nullable=False, default="PERSONAL_ACCOUNT")
    gst_type = Column(String, nullable=False, default="WITH_GST")
    invoice_series = Column(String, nullable=False, default="INV")
    invoice_sequence = Column(Integer, nullable=False, default=1)
    requires_qr = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, default=False, index=True)

    # Invoice lifecycle:
    #   DRAFT → PENDING_VERIFICATION → VERIFIED → SENT
    invoice_status = Column(String, default="DRAFT")  # old "status" kept as alias
    status = Column(String, default="PENDING")        # kept for backwards compatibility
    invoice_number = Column(String, unique=True, index=True)
    whatsapp_sent = Column(Boolean, default=False)
    is_archived = Column(Boolean, nullable=False, default=False)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Service/product description
    service_description = Column(Text, nullable=True, default="Harikrushn DigiVerse LLP Software – Annual Subscription")

    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    shop = relationship("app.modules.shops.models.Shop", backref="bills")
    client = relationship("app.modules.clients.models.Client", backref="bills")
    created_by = relationship("app.modules.users.models.User", foreign_keys=[created_by_id], backref="created_bills")
    verified_by = relationship("app.modules.users.models.User", foreign_keys=[verified_by_id], backref="verified_bills")

    @property
    def shop_name(self) -> str:
        return self.shop.name if self.shop else None

    @property
    def client_name(self) -> str:
        return self.client.name if self.client else self.invoice_client_name
