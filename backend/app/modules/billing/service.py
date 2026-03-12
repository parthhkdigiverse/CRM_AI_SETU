# backend/app/modules/billing/service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request
from app.modules.billing.models import Bill
from app.modules.billing.schemas import BillCreate
from app.modules.shops.models import Shop
from app.modules.clients.models import Client
from app.modules.salary.models import AppSetting
from app.modules.users.models import User, UserRole
import datetime
from datetime import UTC
import uuid


class BillingService:
    def __init__(self, db: Session):
        self.db = db

    # ─────────────────────────────── helpers ────────────────────────────────

    def _next_invoice_number(self) -> str:
        ts = datetime.datetime.now(UTC).strftime('%Y%m%d%H%M%S')
        short = uuid.uuid4().hex[:4].upper()
        return f"INV-{ts}-{short}"

    def get_invoice_defaults(self) -> dict:
        """Return default amount and payment QR settings from app_settings."""
        keys = [
            "invoice_default_amount",
            "payment_upi_id",
            "payment_account_name",
            "payment_qr_image_url",
            "company_name",
            "company_address",
            "company_phone",
            "company_gstin",
        ]
        rows = self.db.query(AppSetting).filter(AppSetting.key.in_(keys)).all()
        mapping = {r.key: r.value for r in rows}
        return {
            "invoice_default_amount": float(mapping.get("invoice_default_amount") or 12000),
            "payment_upi_id": mapping.get("payment_upi_id") or "",
            "payment_account_name": mapping.get("payment_account_name") or "CRM AI SETU",
            "payment_qr_image_url": mapping.get("payment_qr_image_url") or "",
            "company_name": mapping.get("company_name") or "CRM AI SETU",
            "company_address": mapping.get("company_address") or "",
            "company_phone": mapping.get("company_phone") or "",
            "company_gstin": mapping.get("company_gstin") or "",
        }

    def save_invoice_settings(self, payload: dict) -> dict:
        allowed = {
            "invoice_default_amount",
            "payment_upi_id",
            "payment_account_name",
            "payment_qr_image_url",
            "company_name",
            "company_address",
            "company_phone",
            "company_gstin",
        }
        for key, value in payload.items():
            if key not in allowed:
                continue
            setting = self.db.query(AppSetting).filter(AppSetting.key == key).first()
            if setting:
                setting.value = str(value)
            else:
                self.db.add(AppSetting(key=key, value=str(value)))
        self.db.commit()
        return self.get_invoice_defaults()

    # ─────────────────────────────── CRUD ────────────────────────────────────

    def create_invoice(self, bill_in: BillCreate, current_user: User) -> Bill:
        """Create a new invoice in DRAFT status."""
        # Try to find existing client by phone
        existing_client = None
        if bill_in.invoice_client_phone:
            existing_client = (
                self.db.query(Client)
                .filter(Client.phone == bill_in.invoice_client_phone.strip())
                .first()
            )

        db_bill = Bill(
            shop_id=bill_in.shop_id,
            client_id=existing_client.id if existing_client else None,
            invoice_client_name=bill_in.invoice_client_name,
            invoice_client_phone=bill_in.invoice_client_phone,
            invoice_client_email=bill_in.invoice_client_email,
            invoice_client_address=bill_in.invoice_client_address,
            invoice_client_org=bill_in.invoice_client_org,
            amount=bill_in.amount,
            service_description=bill_in.service_description,
            invoice_number=self._next_invoice_number(),
            invoice_status="PENDING_VERIFICATION",
            status="PENDING",
            created_by_id=current_user.id,
        )
        self.db.add(db_bill)
        self.db.commit()
        self.db.refresh(db_bill)
        return db_bill

    def get_bill(self, bill_id: int) -> Bill | None:
        return self.db.query(Bill).filter(Bill.id == bill_id).first()

    def get_all_bills(self, current_user: User, skip: int = 0, limit: int = 200):
        """Return bills filtered by role."""
        q = self.db.query(Bill)
        if current_user.role == UserRole.ADMIN:
            pass  # see all
        elif current_user.role in (UserRole.SALES, UserRole.TELESALES):
            q = q.filter(Bill.created_by_id == current_user.id)
        elif current_user.role == UserRole.PROJECT_MANAGER:
            q = q.filter(Bill.created_by_id == current_user.id)
        else:
            q = q.filter(Bill.created_by_id == current_user.id)
        return q.order_by(Bill.created_at.desc()).offset(skip).limit(limit).all()

    def verify_invoice(self, bill_id: int, current_user: User) -> Bill:
        """Admin verifies the invoice. Changes status to VERIFIED."""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admin can verify invoices")
        bill = self.get_bill(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if bill.invoice_status not in ("PENDING_VERIFICATION", "DRAFT"):
            raise HTTPException(status_code=400, detail=f"Invoice cannot be verified from status '{bill.invoice_status}'")
        bill.invoice_status = "VERIFIED"
        bill.verified_by_id = current_user.id
        bill.verified_at = datetime.datetime.now(UTC)
        self.db.commit()
        self.db.refresh(bill)
        return bill

    async def send_whatsapp_invoice(self, bill_id: int, current_user: User) -> Bill:
        """
        Send invoice to client via WhatsApp.
        Auto-creates the client if they don't exist.
        Marks invoice as SENT.
        """
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admin can send invoices")
        bill = self.get_bill(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if bill.invoice_status != "VERIFIED":
            raise HTTPException(status_code=400, detail="Invoice must be VERIFIED before sending")

        # Auto-create client if not already linked
        if not bill.client_id:
            client = self._ensure_client(bill, current_user)
            bill.client_id = client.id

        bill.invoice_status = "SENT"
        bill.status = "PENDING"
        bill.whatsapp_sent = True
        self.db.commit()
        self.db.refresh(bill)

        # Build WhatsApp message
        settings = self.get_invoice_defaults()
        upi_id = settings.get("payment_upi_id", "")
        message_lines = [
            f"Hello {bill.invoice_client_name},",
            f"",
            f"Your invoice *{bill.invoice_number}* has been generated.",
            f"Amount: *₹{bill.amount:,.0f}*",
            f"Service: {bill.service_description or 'CRM AI SETU Software'}",
            f"",
        ]
        if upi_id:
            message_lines.append(f"💳 Pay via UPI: *{upi_id}*")
            message_lines.append(f"")
        message_lines.append(f"Thank you for choosing {settings['company_name']}!")

        message = "\n".join(message_lines)
        phone = bill.invoice_client_phone.replace("+", "").replace("-", "").replace(" ", "")
        if not phone.startswith("91") and len(phone) == 10:
            phone = "91" + phone
        wa_url = f"https://wa.me/{phone}?text={message.replace(' ', '%20').replace('\n', '%0A')}"

        print(f"--- WHATSAPP INVOICE SEND ---")
        print(f"To: {bill.invoice_client_phone}  ({bill.invoice_client_name})")
        print(f"Invoice: {bill.invoice_number}  Amount: ₹{bill.amount:,.0f}")
        print(f"WA URL: {wa_url}")
        print(f"----------------------------")

        return {"bill": bill, "wa_url": wa_url}

    def _ensure_client(self, bill: Bill, current_user: User) -> Client:
        """Find or create a Client record from the invoice's client snapshot."""
        existing = None
        if bill.invoice_client_phone:
            existing = (
                self.db.query(Client)
                .filter(Client.phone == bill.invoice_client_phone)
                .first()
            )
        if bill.invoice_client_email and not existing:
            existing = (
                self.db.query(Client)
                .filter(Client.email == bill.invoice_client_email)
                .first()
            )
        if existing:
            return existing

        email = bill.invoice_client_email or f"client_{uuid.uuid4().hex[:8]}@placeholder.com"
        client = Client(
            name=bill.invoice_client_name,
            email=email,
            phone=bill.invoice_client_phone,
            organization=bill.invoice_client_org,
            address=bill.invoice_client_address,
            owner_id=current_user.id,
            is_active=True,
        )
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    # now kept for backwards compatibility
    async def generate_bill_and_convert(self, bill_in, current_user, request):
        return self.create_invoice(bill_in, current_user)

    async def confirm_bill(self, bill_id: int, current_user: User, request: Request):
        return self.verify_invoice(bill_id, current_user)

