# backend/app/modules/billing/service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, Request
from sqlalchemy import or_
from app.modules.billing.models import Bill
from app.modules.billing.schemas import BillCreate, BillingWorkflowResolveRequest
from app.modules.clients.models import Client
from app.modules.salary.models import AppSetting
from app.modules.users.models import User, UserRole
from app.core.config import settings
import datetime
from datetime import UTC
import uuid
import hmac as _hmac
import hashlib
from urllib.parse import quote


class BillingService:
    def __init__(self, db: Session):
        self.db = db

    # ─────────────────────────────── helpers ────────────────────────────────

    def _get_setting(self, key: str, default: str = "") -> str:
        row = self.db.query(AppSetting).filter(AppSetting.key == key).first()
        return row.value if row and row.value is not None else default

    def _set_setting(self, key: str, value: str) -> None:
        row = self.db.query(AppSetting).filter(AppSetting.key == key).first()
        if row:
            row.value = value
        else:
            self.db.add(AppSetting(key=key, value=value))

    def _next_invoice_number(self, gst_type: str) -> tuple[str, str, int]:
        year = datetime.datetime.now(UTC).year
        if gst_type == "WITHOUT_GST":
            seq_key = "invoice_seq_without_gst"
            series = "PINV"
            prefix = "PInv"
        else:
            seq_key = "invoice_seq_with_gst"
            series = "INV"
            prefix = "Inv"

        start = int(self._get_setting(seq_key, "1") or "1")
        current = max(start, 1)

        while True:
            invoice_number = f"{prefix}/{year}/{current:03d}"
            exists = self.db.query(Bill.id).filter(Bill.invoice_number == invoice_number).first()
            if not exists:
                break
            current += 1

        # Persist the next sequence pointer so future creates continue correctly.
        self._set_setting(seq_key, str(current + 1))
        return invoice_number, series, current

    def _allowed_verifier_roles(self) -> set[str]:
        raw = (self._get_setting("invoice_verifier_roles", "ADMIN") or "ADMIN").strip()
        roles = {r.strip().upper() for r in raw.split(",") if r.strip()}
        return roles or {"ADMIN"}

    def _current_role_name(self, current_user: User) -> str:
        return current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)

    def _can_verify_or_send(self, current_user: User) -> bool:
        role_name = self._current_role_name(current_user)
        return role_name in self._allowed_verifier_roles()

    def _validate_payment_mode(self, payment_type: str, gst_type: str) -> None:
        if payment_type == "BUSINESS_ACCOUNT" and gst_type != "WITH_GST":
            raise HTTPException(status_code=400, detail="Business account payments must be WITH_GST")
        if payment_type not in {"BUSINESS_ACCOUNT", "PERSONAL_ACCOUNT", "CASH"}:
            raise HTTPException(status_code=400, detail="Invalid payment type")
        if gst_type not in {"WITH_GST", "WITHOUT_GST"}:
            raise HTTPException(status_code=400, detail="Invalid GST type")

    def get_invoice_defaults(self) -> dict:
        """Return default amount and payment QR settings from app_settings."""
        keys = [
            "invoice_default_amount",
            "personal_without_gst_default_amount",
            "payment_upi_id",
            "payment_account_name",
            "payment_qr_image_url",
            "payment_bank_name",
            "payment_account_number",
            "payment_ifsc",
            "payment_branch",
            "company_name",
            "company_address",
            "company_phone",
            "company_email",
            "company_gstin",
            "company_pan",
            "company_cin",
            "company_cst_code",
            "invoice_seq_with_gst",
            "invoice_seq_without_gst",
            "invoice_verifier_roles",
        ]
        rows = self.db.query(AppSetting).filter(AppSetting.key.in_(keys)).all()
        mapping = {r.key: r.value for r in rows}

        def _to_float(val: str | None, fallback: float) -> float:
            try:
                return float(val) if val not in (None, "") else fallback
            except (TypeError, ValueError):
                return fallback

        def _to_int(val: str | None, fallback: int) -> int:
            try:
                return int(val) if val not in (None, "") else fallback
            except (TypeError, ValueError):
                return fallback

        return {
            "invoice_default_amount": _to_float(mapping.get("invoice_default_amount"), 12000),
            "personal_without_gst_default_amount": _to_float(mapping.get("personal_without_gst_default_amount"), 12000),
            "payment_upi_id": mapping.get("payment_upi_id") or "",
            "payment_account_name": mapping.get("payment_account_name") or "HK DigiVerse LLP",
            "payment_qr_image_url": mapping.get("payment_qr_image_url") or "",
            "payment_bank_name": mapping.get("payment_bank_name") or "",
            "payment_account_number": mapping.get("payment_account_number") or "",
            "payment_ifsc": mapping.get("payment_ifsc") or "",
            "payment_branch": mapping.get("payment_branch") or "",
            "company_name": mapping.get("company_name") or "HK DigiVerse LLP",
            "company_address": mapping.get("company_address") or "501-502, Silver Trade Center, near Pragati IT Park, Mota Varachha, Surat, Gujarat, India-394101",
            "company_phone": mapping.get("company_phone") or "+91 8866005029",
            "company_email": mapping.get("company_email") or "hetrmangukiya@gmail.com",
            "company_gstin": mapping.get("company_gstin") or "",
            "company_pan": mapping.get("company_pan") or "",
            "company_cin": mapping.get("company_cin") or "",
            "company_cst_code": mapping.get("company_cst_code") or "",
            "invoice_seq_with_gst": _to_int(mapping.get("invoice_seq_with_gst"), 1),
            "invoice_seq_without_gst": _to_int(mapping.get("invoice_seq_without_gst"), 1),
            "invoice_verifier_roles": mapping.get("invoice_verifier_roles") or "ADMIN",
        }

    def get_workflow_options(self, current_user: User) -> dict:
        settings = self.get_invoice_defaults()
        allowed_roles = sorted(self._allowed_verifier_roles())
        return {
            "payment_types": ["BUSINESS_ACCOUNT", "PERSONAL_ACCOUNT", "CASH"],
            "gst_types": ["WITH_GST", "WITHOUT_GST"],
            "constraints": {
                "BUSINESS_ACCOUNT": {"allowed_gst_types": ["WITH_GST"]},
                "PERSONAL_ACCOUNT": {"allowed_gst_types": ["WITH_GST", "WITHOUT_GST"]},
                "CASH": {"allowed_gst_types": ["WITH_GST", "WITHOUT_GST"]},
            },
            "defaults": {
                "invoice_default_amount": settings["invoice_default_amount"],
                "personal_without_gst_default_amount": settings["personal_without_gst_default_amount"],
                "payment_type": "PERSONAL_ACCOUNT",
                "gst_type": "WITH_GST",
            },
            "permissions": {
                "allowed_verifier_roles": allowed_roles,
                "can_verify_or_send": self._can_verify_or_send(current_user),
            },
        }

    def resolve_workflow(self, req: BillingWorkflowResolveRequest) -> dict:
        self._validate_payment_mode(req.payment_type, req.gst_type)
        settings = self.get_invoice_defaults()

        amount_source = "client_input"
        base_amount = req.amount
        if base_amount is None:
            if req.payment_type == "PERSONAL_ACCOUNT" and req.gst_type == "WITHOUT_GST":
                base_amount = float(settings.get("personal_without_gst_default_amount") or 12000)
                amount_source = "personal_without_gst_default_amount"
            else:
                base_amount = float(settings.get("invoice_default_amount") or 12000)
                amount_source = "invoice_default_amount"

        if base_amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")

        if req.gst_type == "WITH_GST":
            gst_amount = round(base_amount * 0.18, 2)
            total_amount = round(base_amount + gst_amount, 2)
        else:
            gst_amount = 0.0
            total_amount = round(base_amount, 2)

        requires_qr = req.payment_type != "CASH"
        qr_available = bool(settings.get("payment_qr_image_url") or settings.get("payment_upi_id"))
        if requires_qr and not qr_available:
            raise HTTPException(status_code=400, detail="Payment QR/UPI is not configured in settings")

        return {
            "payment_type": req.payment_type,
            "gst_type": req.gst_type,
            "requires_qr": requires_qr,
            "amount": total_amount,
            "base_amount": base_amount,
            "gst_amount": gst_amount,
            "total_amount": total_amount,
            "amount_source": amount_source,
            "qr_available": qr_available,
            "qr_image_url": settings.get("payment_qr_image_url") or None,
            "payment_upi_id": settings.get("payment_upi_id") or None,
            "payment_account_name": settings.get("payment_account_name") or None,
        }

    def get_invoice_actions(self, bill: Bill, current_user: User) -> dict:
        can_verify = self._can_verify_or_send(current_user) and bill.invoice_status in {"DRAFT", "PENDING_VERIFICATION"}
        can_send_whatsapp = self._can_verify_or_send(current_user) and bill.invoice_status == "VERIFIED"
        return {
            "can_verify": can_verify,
            "can_send_whatsapp": can_send_whatsapp,
            "allowed_verifier_roles": sorted(self._allowed_verifier_roles()),
        }

    def save_invoice_settings(self, payload: dict) -> dict:
        allowed = {
            "invoice_default_amount",
            "personal_without_gst_default_amount",
            "payment_upi_id",
            "payment_account_name",
            "payment_qr_image_url",
            "payment_bank_name",
            "payment_account_number",
            "payment_ifsc",
            "payment_branch",
            "company_name",
            "company_address",
            "company_phone",
            "company_email",
            "company_gstin",
            "company_pan",
            "company_cin",
            "company_cst_code",
            "invoice_seq_with_gst",
            "invoice_seq_without_gst",
            "invoice_verifier_roles",
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
        self._validate_payment_mode(bill_in.payment_type, bill_in.gst_type)

        resolved = self.resolve_workflow(
            BillingWorkflowResolveRequest(
                payment_type=bill_in.payment_type,
                gst_type=bill_in.gst_type,
                amount=bill_in.amount,
            )
        )
        amount = resolved["total_amount"]
        requires_qr = resolved["requires_qr"]

        invoice_number, invoice_series, invoice_sequence = self._next_invoice_number(bill_in.gst_type)

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
            amount=amount,
            payment_type=bill_in.payment_type,
            gst_type=bill_in.gst_type,
            invoice_series=invoice_series,
            invoice_sequence=invoice_sequence,
            requires_qr=requires_qr,
            service_description=bill_in.service_description,
            invoice_number=invoice_number,
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

    def get_all_bills(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 200,
        status_filter: str | None = None,
        payment_type: str | None = None,
        gst_type: str | None = None,
        search: str | None = None,
    ):
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

        if status_filter and status_filter.upper() != "ALL":
            status_filter = status_filter.upper()
            q = q.filter(or_(Bill.invoice_status == status_filter, Bill.status == status_filter))
        if payment_type and payment_type.upper() != "ALL":
            q = q.filter(Bill.payment_type == payment_type.upper())
        if gst_type and gst_type.upper() != "ALL":
            q = q.filter(Bill.gst_type == gst_type.upper())
        if search:
            token = f"%{search.strip()}%"
            q = q.filter(or_(
                Bill.invoice_number.ilike(token),
                Bill.invoice_client_name.ilike(token),
                Bill.invoice_client_phone.ilike(token),
                Bill.invoice_client_org.ilike(token),
            ))

        return q.order_by(Bill.created_at.desc()).offset(skip).limit(limit).all()

    def verify_invoice(self, bill_id: int, current_user: User) -> Bill:
        """Verify invoice. Allowed roles are controlled by invoice settings."""
        if not self._can_verify_or_send(current_user):
            raise HTTPException(status_code=403, detail="You do not have permission to verify invoices")
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

    @staticmethod
    def _invoice_public_token(bill_id: int) -> str:
        """HMAC-SHA256 token for unauthenticated invoice viewing."""
        key = settings.SECRET_KEY.encode()
        msg = f"invoice-public-{bill_id}".encode()
        return _hmac.new(key, msg, hashlib.sha256).hexdigest()[:32]

    def _build_whatsapp_message(self, bill: Bill, invoice_settings: dict, invoice_url: str = "") -> str:
        upi_id = invoice_settings.get("payment_upi_id", "")
        message_lines = [
            f"Hello {bill.invoice_client_name},",
            "",
            f"Your invoice *{bill.invoice_number}* has been generated.",
            f"Amount: *₹{bill.amount:,.0f}*",
            f"Service: {bill.service_description or 'CRM AI SETU Software'}",
            "",
        ]
        if invoice_url:
            message_lines.append(f"📄 View & Download Invoice: {invoice_url}")
            message_lines.append("")
        if upi_id:
            message_lines.append(f"💳 Pay via UPI: *{upi_id}*")
            message_lines.append("")
        message_lines.append(f"Thank you for choosing {invoice_settings['company_name']}!")
        return "\n".join(message_lines)

    @staticmethod
    def _normalize_indian_phone(raw_phone: str) -> str:
        phone = raw_phone.replace("+", "").replace("-", "").replace(" ", "")
        if not phone.startswith("91") and len(phone) == 10:
            phone = "91" + phone
        return phone

    @staticmethod
    def _build_whatsapp_url(phone: str, message: str) -> str:
        return f"https://wa.me/{phone}?text={quote(message)}"

    def _send_whatsapp_via_gateway(self, phone: str, message: str) -> None:
        # ─────────────────────────────────────────────────────────────────────
        # META WHATSAPP CLOUD API INTEGRATION (currently disabled)
        #
        # HOW TO ENABLE:
        #   1. Go to https://developers.facebook.com → Create App → Business
        #   2. Add "WhatsApp" product → get a dedicated phone number
        #   3. Copy your Phone Number ID and permanent Access Token
        #   4. Add to your .env file:
        #        WHATSAPP_TOKEN=EAAxxxxxxxxxxxxxxxx
        #        WHATSAPP_PHONE_NUMBER_ID=123456789012345
        #   5. Uncomment the block below (remove the leading #  from each line)
        #
        # FREE TIER: 1,000 conversations/month at no cost.
        # The message is sent server-side — no browser or WhatsApp Web needed.
        # ─────────────────────────────────────────────────────────────────────
        #
        # import httpx
        # token   = settings.WHATSAPP_TOKEN            # from .env
        # phone_id = settings.WHATSAPP_PHONE_NUMBER_ID  # from .env
        # url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
        # headers = {
        #     "Authorization": f"Bearer {token}",
        #     "Content-Type": "application/json",
        # }
        # payload = {
        #     "messaging_product": "whatsapp",
        #     "to": phone,                   # e.g. "919876543210"
        #     "type": "text",
        #     "text": {"body": message},
        # }
        # with httpx.Client(timeout=10) as client:
        #     resp = client.post(url, headers=headers, json=payload)
        #     resp.raise_for_status()        # raises on 4xx/5xx
        #
        _ = (phone, message)  # remove this line when enabling above

    def _create_phonepe_payment_link(self, bill: Bill, phone: str) -> str | None:
        # ─────────────────────────────────────────────────────────────────────
        # PHONEPE PAYMENT GATEWAY — PAY PAGE LINK (currently disabled)
        #
        # HOW TO ENABLE:
        #   1. Credentials are already in config.py (test keys loaded from .env)
        #   2. Set PHONEPE_CALLBACK_BASE_URL in .env to your public server URL
        #      e.g.  PHONEPE_CALLBACK_BASE_URL=https://yourdomain.com
        #   3. Uncomment the block below
        #
        # HOW IT WORKS:
        #   - Payload is base64-encoded and signed with SHA256 + salt
        #   - PhonePe returns a hosted payment page URL
        #   - Client opens it and pays via UPI / card / net-banking
        #   - PhonePe POSTs to your /api/billing/phonepe-callback on completion
        #   - Test sandbox: https://api-preprod.phonepe.com/apis/pg-sandbox
        # ─────────────────────────────────────────────────────────────────────
        #
        # import httpx, hashlib, base64, json as _json
        # merchant_id   = settings.PHONEPE_MERCHANT_ID
        # salt_key      = settings.PHONEPE_SALT_KEY
        # salt_index    = settings.PHONEPE_SALT_INDEX
        # is_sandbox    = settings.PHONEPE_ENV != "production"
        # base_api      = (
        #     "https://api-preprod.phonepe.com/apis/pg-sandbox"
        #     if is_sandbox else
        #     "https://api.phonepe.com/apis/hermes"
        # )
        # cb_base = settings.PHONEPE_CALLBACK_BASE_URL.rstrip("/")
        # txn_id  = f"MT-{bill.invoice_number}-{uuid.uuid4().hex[:8]}".replace("/", "-")
        # payload = {
        #     "merchantId":            merchant_id,
        #     "merchantTransactionId": txn_id,
        #     "merchantUserId":        f"MUID-{phone}",
        #     "amount":                int(round(bill.amount * 100)),  # paise
        #     "redirectUrl":           f"{cb_base}/api/billing/phonepe-callback",
        #     "redirectMode":          "POST",
        #     "callbackUrl":           f"{cb_base}/api/billing/phonepe-callback",
        #     "mobileNumber":          phone[-10:],
        #     "paymentInstrument":     {"type": "PAY_PAGE"},
        # }
        # encoded      = base64.b64encode(_json.dumps(payload).encode()).decode()
        # chk_str      = encoded + "/pg/v1/pay" + salt_key
        # checksum     = hashlib.sha256(chk_str.encode()).hexdigest() + "###" + str(salt_index)
        # headers = {
        #     "Content-Type":  "application/json",
        #     "X-VERIFY":      checksum,
        #     "X-MERCHANT-ID": merchant_id,
        # }
        # with httpx.Client(timeout=15) as client:
        #     resp = client.post(f"{base_api}/pg/v1/pay", headers=headers, json={"request": encoded})
        #     resp.raise_for_status()
        #     data = resp.json()
        # if data.get("success"):
        #     return data["data"]["instrumentResponse"]["redirectInfo"]["url"]
        # return None
        #
        _ = (bill, phone)
        return None

    def _create_phonepe_upi_qr(self, bill: Bill, phone: str) -> str | None:
        # ─────────────────────────────────────────────────────────────────────
        # PHONEPE PAYMENT GATEWAY — UPI QR CODE (currently disabled)
        #
        # Enable this to generate a UPI QR image (base64 PNG) that can be
        # embedded directly in the invoice HTML for instant in-person payment.
        # Same prerequisites as _create_phonepe_payment_link above.
        # ─────────────────────────────────────────────────────────────────────
        #
        # import httpx, hashlib, base64, json as _json
        # merchant_id  = settings.PHONEPE_MERCHANT_ID
        # salt_key     = settings.PHONEPE_SALT_KEY
        # salt_index   = settings.PHONEPE_SALT_INDEX
        # is_sandbox   = settings.PHONEPE_ENV != "production"
        # base_api     = (
        #     "https://api-preprod.phonepe.com/apis/pg-sandbox"
        #     if is_sandbox else
        #     "https://api.phonepe.com/apis/hermes"
        # )
        # txn_id  = f"QR-{bill.invoice_number}-{uuid.uuid4().hex[:8]}".replace("/", "-")
        # payload = {
        #     "merchantId":            merchant_id,
        #     "merchantTransactionId": txn_id,
        #     "merchantUserId":        f"MUID-{phone}",
        #     "amount":                int(round(bill.amount * 100)),  # paise
        #     "mobileNumber":          phone[-10:],
        #     "paymentInstrument":     {"type": "UPI_QR"},
        # }
        # encoded  = base64.b64encode(_json.dumps(payload).encode()).decode()
        # chk_str  = encoded + "/pg/v1/pay" + salt_key
        # checksum = hashlib.sha256(chk_str.encode()).hexdigest() + "###" + str(salt_index)
        # headers  = {
        #     "Content-Type":  "application/json",
        #     "X-VERIFY":      checksum,
        #     "X-MERCHANT-ID": merchant_id,
        # }
        # with httpx.Client(timeout=15) as client:
        #     resp = client.post(f"{base_api}/pg/v1/pay", headers=headers, json={"request": encoded})
        #     resp.raise_for_status()
        #     data = resp.json()
        # if data.get("success"):
        #     qr_data = data["data"]["instrumentResponse"]["intentInfo"]["intentUrl"]
        #     # qr_data is a "upi://pay?..." string; convert to image using qrcode lib:
        #     # import qrcode, io
        #     # img = qrcode.make(qr_data)
        #     # buf = io.BytesIO(); img.save(buf, format="PNG")
        #     # return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        #     return qr_data  # or return the base64 image string above
        # return None
        #
        _ = (bill, phone)
        return None

    async def send_whatsapp_invoice(self, bill_id: int, current_user: User, base_url: str = "") -> Bill:
        """
        Send invoice to client via WhatsApp.
        Auto-creates the client if they don't exist.
        Marks invoice as SENT.
        """
        if not self._can_verify_or_send(current_user):
            raise HTTPException(status_code=403, detail="You do not have permission to send invoices")
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
        # Build a public (no-auth) invoice view URL using HMAC token
        invoice_url = ""
        if base_url:
            token = self._invoice_public_token(bill.id)
            invoice_url = f"{base_url.rstrip('/')}api/billing/{bill.id}/invoice-public?token={token}"
        message = self._build_whatsapp_message(bill, settings, invoice_url)
        phone = self._normalize_indian_phone(bill.invoice_client_phone)
        wa_url = self._build_whatsapp_url(phone, message)
        phonepe_payment_link = self._create_phonepe_payment_link(bill, phone)
        self._send_whatsapp_via_gateway(phone, message)

        print(f"--- WHATSAPP INVOICE SEND ---")
        print(f"To: {bill.invoice_client_phone}  ({bill.invoice_client_name})")
        print(f"Invoice: {bill.invoice_number}  Amount: ₹{bill.amount:,.0f}")
        print(f"WA URL: {wa_url}")
        print(f"----------------------------")

        if phonepe_payment_link:
            print(f"PhonePe URL: {phonepe_payment_link}")

        return {
            "bill": bill,
            "wa_url": wa_url,
            "phonepe_payment_link": phonepe_payment_link,
        }

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

