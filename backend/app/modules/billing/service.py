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
import json
import io

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


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

    def _allowed_invoice_creator_roles(self) -> set[str]:
        raw = (
            self._get_setting("invoice_creator_roles", "ADMIN,SALES,TELESALES,PROJECT_MANAGER_AND_SALES")
            or "ADMIN,SALES,TELESALES,PROJECT_MANAGER_AND_SALES"
        ).strip()
        roles = {r.strip().upper() for r in raw.split(",") if r.strip()}
        return roles or {"ADMIN", "SALES", "TELESALES", "PROJECT_MANAGER_AND_SALES"}

    def _can_create_invoice(self, current_user: User) -> bool:
        role_name = self._current_role_name(current_user)
        return role_name in self._allowed_invoice_creator_roles()

    @staticmethod
    def _can_archive_invoice(current_user: User, bill: Bill) -> bool:
        if current_user.role == UserRole.ADMIN:
            return True
        return bill.created_by_id == current_user.id

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
            "invoice_terms_conditions",
            # Business Account fields
            "business_payment_upi_id",
            "business_payment_account_name",
            "business_payment_qr_image_url",
            "business_payment_bank_name",
            "business_payment_account_number",
            "business_payment_ifsc",
            "business_payment_branch",
            # Personal Account fields
            "personal_payment_upi_id",
            "personal_payment_account_name",
            "personal_payment_qr_image_url",
            "personal_payment_bank_name",
            "personal_payment_account_number",
            "personal_payment_ifsc",
            "personal_payment_branch",
            
            # Legacy fallback keys
            "payment_upi_id",
            "payment_account_name",
            "payment_qr_image_url",
            "payment_bank_name",
            "payment_account_number",
            "payment_ifsc",
            "payment_branch",

            "company_name",
            "company_address",
            "company_header_image_details",
            "company_phone",
            "company_email",
            "company_gstin",
            "company_pan",
            "company_cin",
            "company_cst_code",
            "invoice_header_bg",
            "invoice_seq_with_gst",
            "invoice_seq_without_gst",
            "invoice_verifier_roles",
            "invoice_creator_roles",
            "whatsapp_invoice_caption",
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
            "invoice_terms_conditions": mapping.get("invoice_terms_conditions") or "• Subject to Surat Jurisdiction",
            "payment_upi_id": mapping.get("payment_upi_id") or "",
            "payment_account_name": mapping.get("payment_account_name") or "Harikrushn DigiVerse LLP",
            "payment_qr_image_url": mapping.get("payment_qr_image_url") or "",
            "payment_bank_name": mapping.get("payment_bank_name") or "",
            "payment_account_number": mapping.get("payment_account_number") or "",
            "payment_ifsc": mapping.get("payment_ifsc") or "",
            "payment_branch": mapping.get("payment_branch") or "",
            "company_name": mapping.get("company_name") or "Harikrushn DigiVerse LLP",
            "company_address": mapping.get("company_address") or "501-502, Silver Trade Center, near Pragati IT Park, Mota Varachha, Surat, Gujarat, India-394101",
            "company_header_image_details": mapping.get("company_header_image_details") or "",
            "company_phone": mapping.get("company_phone") or "+91 8866005029",
            "company_email": mapping.get("company_email") or "hetrmangukiya@gmail.com",
            "company_gstin": mapping.get("company_gstin") or "",
            "company_pan": mapping.get("company_pan") or "",
            "company_cin": mapping.get("company_cin") or "",
            "company_cst_code": mapping.get("company_cst_code") or "",
            "invoice_header_bg": mapping.get("invoice_header_bg") or "#2E5B82",
            "invoice_seq_with_gst": _to_int(mapping.get("invoice_seq_with_gst"), 1),
            "invoice_seq_without_gst": _to_int(mapping.get("invoice_seq_without_gst"), 1),
            "invoice_verifier_roles": mapping.get("invoice_verifier_roles") or "ADMIN",
            "invoice_creator_roles": mapping.get("invoice_creator_roles") or "ADMIN,SALES,TELESALES,PROJECT_MANAGER_AND_SALES",
            "whatsapp_invoice_caption": mapping.get("whatsapp_invoice_caption") or "Please find your invoice attached.",
        }

    def get_workflow_options(self, current_user: User) -> dict:
        settings = self.get_invoice_defaults()
        allowed_roles = sorted(self._allowed_verifier_roles())
        allowed_creator_roles = sorted(self._allowed_invoice_creator_roles())
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
                "allowed_creator_roles": allowed_creator_roles,
                "can_create_invoice": self._can_create_invoice(current_user),
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
        can_verify = self._can_verify_or_send(current_user) and (not bool(bill.is_archived)) and bill.invoice_status in {"DRAFT", "PENDING_VERIFICATION"}
        can_send_whatsapp = self._can_verify_or_send(current_user) and (not bool(bill.is_archived)) and bill.invoice_status == "VERIFIED"
        can_archive = self._can_archive_invoice(current_user, bill) and (not bool(bill.is_archived))
        can_unarchive = self._can_archive_invoice(current_user, bill) and bool(bill.is_archived)
        can_delete_archived = self._can_archive_invoice(current_user, bill) and bool(bill.is_archived)
        return {
            "can_verify": can_verify,
            "can_send_whatsapp": can_send_whatsapp,
            "can_archive": can_archive,
            "can_unarchive": can_unarchive,
            "can_delete_archived": can_delete_archived,
            "allowed_verifier_roles": sorted(self._allowed_verifier_roles()),
        }

    def save_invoice_settings(self, payload: dict) -> dict:
        allowed = {
            "invoice_default_amount",
            "personal_without_gst_default_amount",
            "invoice_terms_conditions",
            # Business Account fields
            "business_payment_upi_id",
            "business_payment_account_name",
            "business_payment_qr_image_url",
            "business_payment_bank_name",
            "business_payment_account_number",
            "business_payment_ifsc",
            "business_payment_branch",
            # Personal Account fields
            "personal_payment_upi_id",
            "personal_payment_account_name",
            "personal_payment_qr_image_url",
            "personal_payment_bank_name",
            "personal_payment_account_number",
            "personal_payment_ifsc",
            "personal_payment_branch",
            # Legacy fallback keys
            "payment_upi_id",
            "payment_account_name",
            "payment_qr_image_url",
            "payment_bank_name",
            "payment_account_number",
            "payment_ifsc",
            "payment_branch",

            "company_name",
            "company_address",
            "company_header_image_details",
            "company_phone",
            "company_email",
            "company_gstin",
            "company_pan",
            "company_cin",
            "company_cst_code",
            "invoice_header_bg",
            "invoice_seq_with_gst",
            "invoice_seq_without_gst",
            "invoice_verifier_roles",
            "invoice_creator_roles",
            "whatsapp_invoice_caption",
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

        if not self._can_create_invoice(current_user):
            raise HTTPException(status_code=403, detail="You do not have permission to create invoices")

        if bill_in.invoice_client_phone:
            active_bill = self.db.query(Bill).filter(
                Bill.invoice_client_phone == bill_in.invoice_client_phone.strip(),
                Bill.is_archived == False,
                Bill.is_deleted == False
            ).first()
            if active_bill:
                raise HTTPException(
                    status_code=400,
                    detail="An active invoice already exists for this client's phone number. Please archive the existing invoice before generating a new one."
                )

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

        if existing_client and current_user.role != UserRole.ADMIN:
            can_use_existing_client = (
                existing_client.owner_id == current_user.id
                or existing_client.pm_id == current_user.id
                or existing_client.referred_by_id == current_user.id
            )
            if not can_use_existing_client:
                raise HTTPException(
                    status_code=403,
                    detail="You can create invoice only for your own client or a new client"
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
        policy = self.db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
        query = self.db.query(Bill).filter(Bill.id == bill_id)
        if not policy or policy.value == "SOFT":
            query = query.filter(Bill.is_deleted == False)
        return query.first()

    def get_all_bills(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 200,
        status_filter: str | None = None,
        archived: str | None = "ACTIVE",
        payment_type: str | None = None,
        gst_type: str | None = None,
        search: str | None = None,
    ):
        """Return bills filtered by role."""
        policy = self.db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
        q = self.db.query(Bill)
        
        if not policy or policy.value == "SOFT":
            q = q.filter(Bill.is_deleted == False)
            
        if current_user.role == UserRole.ADMIN:
            pass  # see all
        elif current_user.role in (UserRole.SALES, UserRole.TELESALES):
            q = q.filter(Bill.created_by_id == current_user.id)
        elif current_user.role == UserRole.PROJECT_MANAGER:
            q = q.filter(Bill.created_by_id == current_user.id)
        else:
            q = q.filter(Bill.created_by_id == current_user.id)

        archived_mode = (archived or "ACTIVE").upper()
        if archived_mode == "ARCHIVED":
            q = q.filter(Bill.is_archived.is_(True))
        elif archived_mode != "ALL":
            q = q.filter(Bill.is_archived.is_(False))

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
        if bill.is_archived:
            raise HTTPException(status_code=400, detail="Archived invoice cannot be verified")
        if bill.invoice_status not in ("PENDING_VERIFICATION", "DRAFT"):
            raise HTTPException(status_code=400, detail=f"Invoice cannot be verified from status '{bill.invoice_status}'")
        bill.invoice_status = "VERIFIED"
        bill.verified_by_id = current_user.id
        bill.verified_at = datetime.datetime.now(UTC)
        self.db.commit()
        self.db.refresh(bill)
        return bill

    def archive_invoice(self, bill_id: int, current_user: User) -> Bill:
        bill = self.get_bill(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if not self._can_archive_invoice(current_user, bill):
            raise HTTPException(status_code=403, detail="You do not have permission to archive this invoice")
        if bill.is_archived:
            return bill
        bill.is_archived = True
        self.db.commit()
        self.db.refresh(bill)
        return bill

    def unarchive_invoice(self, bill_id: int, current_user: User) -> Bill:
        bill = self.get_bill(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if not self._can_archive_invoice(current_user, bill):
            raise HTTPException(status_code=403, detail="You do not have permission to unarchive this invoice")
        if not bill.is_archived:
            return bill
        bill.is_archived = False
        self.db.commit()
        self.db.refresh(bill)
        return bill

    def archive_invoices_bulk(self, bill_ids: list[int], current_user: User) -> dict:
        ids = sorted({int(i) for i in (bill_ids or []) if str(i).strip()})
        if not ids:
            raise HTTPException(status_code=400, detail="No invoice ids provided")

        rows = self.db.query(Bill).filter(Bill.id.in_(ids), Bill.is_deleted == False).all()
        updated = 0
        for bill in rows:
            if self._can_archive_invoice(current_user, bill) and not bool(bill.is_archived):
                bill.is_archived = True
                updated += 1
        self.db.commit()
        return {
            "requested": len(ids),
            "matched": len(rows),
            "archived": updated,
        }

    def delete_archived_invoice(self, bill_id: int, current_user: User) -> dict:
        bill = self.get_bill(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if not self._can_archive_invoice(current_user, bill):
            raise HTTPException(status_code=403, detail="You do not have permission to delete this invoice")
        if not bill.is_archived:
            raise HTTPException(status_code=400, detail="Only archived invoices can be deleted")

        policy = self.db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
        is_hard = bool(policy and policy.value == "HARD")
        if is_hard:
            self.db.delete(bill)
        else:
            bill.is_deleted = True
            if "-del-" not in bill.invoice_number:
                bill.invoice_number = f"{bill.invoice_number}-del-{bill.id}"
        self.db.commit()
        return {"success": True, "deleted": 1}

    def delete_archived_invoices_bulk(self, bill_ids: list[int], current_user: User) -> dict:
        ids = sorted({int(i) for i in (bill_ids or []) if str(i).strip()})
        if not ids:
            raise HTTPException(status_code=400, detail="No invoice ids provided")

        rows = self.db.query(Bill).filter(Bill.id.in_(ids), Bill.is_deleted == False).all()
        policy = self.db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
        is_hard = bool(policy and policy.value == "HARD")
        deleted = 0

        for bill in rows:
            if not self._can_archive_invoice(current_user, bill):
                continue
            if not bill.is_archived:
                continue
            if is_hard:
                self.db.delete(bill)
            else:
                bill.is_deleted = True
                if "-del-" not in bill.invoice_number:
                    bill.invoice_number = f"{bill.invoice_number}-del-{bill.id}"
            deleted += 1

        self.db.commit()
        return {
            "requested": len(ids),
            "matched": len(rows),
            "deleted": deleted,
        }

    @staticmethod
    def _invoice_public_token(bill_id: int) -> str:
        """HMAC-SHA256 token for unauthenticated invoice viewing."""
        key = settings.SECRET_KEY.encode()
        msg = f"invoice-public-{bill_id}".encode()
        return _hmac.new(key, msg, hashlib.sha256).hexdigest()[:32]

    def _build_whatsapp_caption(self, invoice_settings: dict) -> str:
        caption = (invoice_settings.get("whatsapp_invoice_caption") or "").strip()
        if caption:
            return caption
        company_name = invoice_settings.get("company_name") or "Harikrushn DigiVerse LLP"
        return f"Please find your invoice attached. Thank you for choosing {company_name}."

    @staticmethod
    def _normalize_indian_phone(raw_phone: str) -> str:
        phone = raw_phone.replace("+", "").replace("-", "").replace(" ", "")
        if not phone.startswith("91") and len(phone) == 10:
            phone = "91" + phone
        return phone

    def _fetch_invoice_pdf_bytes(self, document_url: str) -> bytes:
        import httpx

        try:
            with httpx.Client(timeout=20) as client:
                resp = client.get(document_url)
                resp.raise_for_status()
                return resp.content
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Could not fetch invoice PDF for WhatsApp upload: {exc}")

    @staticmethod
    def _build_invoice_pdf_bytes(bill: Bill, invoice_settings: dict, qr_image_b64: str = None) -> bytes:
        """Build invoice PDF bytes directly to avoid self-calling API over HTTP."""
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        width, height = A4

        x = 40
        y = height - 40

        company_name = invoice_settings.get("company_name") or "Harikrushn DigiVerse LLP"
        company_address = invoice_settings.get("company_address") or ""
        company_gst = invoice_settings.get("company_gst") or ""
        
        prefix = "business_" if bill.payment_type == "BUSINESS_ACCOUNT" else "personal_" if bill.payment_type == "PERSONAL_ACCOUNT" else ""
        payment_upi = invoice_settings.get(f"{prefix}payment_upi_id") or invoice_settings.get("payment_upi_id") or ""

        c.setFont("Helvetica-Bold", 15)
        c.drawString(x, y, company_name)
        y -= 20

        c.setFont("Helvetica", 10)
        if company_address:
            for line in [p.strip() for p in company_address.split("\n") if p.strip()]:
                c.drawString(x, y, line)
                y -= 14
        if company_gst:
            c.drawString(x, y, f"GSTIN: {company_gst}")
            y -= 14

        y -= 10
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "Tax Invoice")
        y -= 24

        c.setFont("Helvetica", 10)
        c.drawString(x, y, f"Invoice No: {bill.invoice_number or '-'}")
        y -= 14
        c.drawString(x, y, f"Date: {bill.created_at.strftime('%d-%m-%Y') if bill.created_at else '-'}")
        y -= 22

        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, y, "Bill To:")
        y -= 14

        c.setFont("Helvetica", 10)
        c.drawString(x, y, bill.invoice_client_name or "-")
        y -= 14
        if bill.invoice_client_phone:
            c.drawString(x, y, f"Phone: {bill.invoice_client_phone}")
            y -= 14
        if bill.invoice_client_org:
            c.drawString(x, y, bill.invoice_client_org)
            y -= 14
        if bill.invoice_client_address:
            for line in [p.strip() for p in bill.invoice_client_address.split("\n") if p.strip()]:
                c.drawString(x, y, line)
                y -= 14

        y -= 14
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, y, "Description")
        c.drawString(width - 170, y, "Amount (INR)")
        y -= 12
        c.line(x, y, width - 40, y)
        y -= 16

        c.setFont("Helvetica", 10)
        c.drawString(x, y, (bill.service_description or "Harikrushn DigiVerse LLP Software – Annual Subscription")[:80])
        c.drawRightString(width - 40, y, f"{float(bill.amount):,.2f}")
        y -= 16
        c.line(x, y, width - 40, y)
        y -= 16

        c.setFont("Helvetica-Bold", 11)
        c.drawString(width - 170, y, "Total")
        c.drawRightString(width - 40, y, f"INR {float(bill.amount):,.2f}")
        y -= 28

        c.setFont("Helvetica", 9)
        if payment_upi:
            c.drawString(x, y, f"UPI: {payment_upi}")
            y -= 13

        # Add QR Image if provided
        if qr_image_b64:
            try:
                # qr_image_b64 is "data:image/png;base64,...."
                header, encoded = qr_image_b64.split(",", 1)
                import base64
                img_data = base64.b64decode(encoded)
                from reportlab.lib.utils import ImageReader
                img_reader = ImageReader(io.BytesIO(img_data))
                c.drawImage(img_reader, x, y - 85, width=80, height=80)
                y -= 95
            except Exception:
                pass

        c.drawString(x, y, "This is a system-generated invoice.")

        c.showPage()
        c.save()
        return buf.getvalue()

    @staticmethod
    def _parse_meta_error(resp_text: str) -> dict:
        try:
            data = json.loads(resp_text)
            err = (data or {}).get("error") or {}
            msg = err.get("message") or "Unknown WhatsApp error"
            code = err.get("code")
            subcode = err.get("error_subcode")
            return {
                "message": msg,
                "code": code,
                "subcode": subcode,
            }
        except Exception:
            return {
                "message": resp_text[:500],
                "code": None,
                "subcode": None,
            }

    @staticmethod
    def _extract_meta_error(resp_text: str) -> str:
        err = BillingService._parse_meta_error(resp_text)
        msg = err.get("message") or "Unknown WhatsApp error"
        code = err.get("code")
        subcode = err.get("subcode")
        if code and subcode:
            return f"{msg} (code={code}, subcode={subcode})"
        if code:
            return f"{msg} (code={code})"
        return msg

    @staticmethod
    def _is_meta_auth_error(meta_error: dict) -> bool:
        try:
            return int(meta_error.get("code") or 0) == 190
        except Exception:
            return False

    def _get_whatsapp_tokens(self) -> list[str]:
        tokens: list[str] = []
        primary = (settings.WHATSAPP_TOKEN or "").strip()
        fallback = (settings.WHATSAPP_TOKEN_FALLBACK or "").strip()
        for token in (primary, fallback):
            if token and token not in tokens:
                tokens.append(token)
        return tokens

    def _upload_whatsapp_media(self, pdf_bytes: bytes, filename: str) -> str:
        import httpx

        tokens = self._get_whatsapp_tokens()
        phone_id = settings.WHATSAPP_PHONE_NUMBER_ID.strip()
        if not tokens or not phone_id:
            raise HTTPException(status_code=500, detail="WhatsApp API is not configured")

        upload_url = f"https://graph.facebook.com/v19.0/{phone_id}/media"
        form_data = {
            "messaging_product": "whatsapp",
            "type": "application/pdf",
        }
        files = {
            "file": (filename, pdf_bytes, "application/pdf"),
        }

        try:
            with httpx.Client(timeout=30) as client:
                last_auth_error = None
                for token in tokens:
                    headers = {
                        "Authorization": f"Bearer {token}",
                    }
                    resp = client.post(upload_url, headers=headers, data=form_data, files=files)
                    if resp.status_code < 400:
                        payload = resp.json()
                        media_id = (payload or {}).get("id")
                        if not media_id:
                            raise HTTPException(status_code=502, detail="WhatsApp media upload failed: missing media id")
                        return media_id

                    meta_error = self._parse_meta_error(resp.text)
                    if self._is_meta_auth_error(meta_error):
                        last_auth_error = self._extract_meta_error(resp.text)
                        continue

                    message = self._extract_meta_error(resp.text)
                    raise HTTPException(status_code=502, detail=f"WhatsApp media upload failed: {message}")

                if last_auth_error:
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            "WhatsApp media upload failed: token authentication failed. "
                            "Update WHATSAPP_TOKEN (or WHATSAPP_TOKEN_FALLBACK) with a valid permanent token and restart backend. "
                            f"Meta: {last_auth_error}"
                        ),
                    )

                raise HTTPException(status_code=502, detail="WhatsApp media upload failed")
        except HTTPException:
            raise
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"WhatsApp media upload failed: {exc}")

    def _send_whatsapp_via_gateway(self, phone: str, media_id: str, caption: str, filename: str) -> None:
        import httpx

        tokens = self._get_whatsapp_tokens()
        phone_id = settings.WHATSAPP_PHONE_NUMBER_ID.strip()
        if not tokens or not phone_id:
            raise HTTPException(status_code=500, detail="WhatsApp API is not configured")

        url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "document",
            "document": {
                "id": media_id,
                "caption": caption,
                "filename": filename,
            },
        }
        try:
            with httpx.Client(timeout=10) as client:
                last_auth_error = None
                for token in tokens:
                    headers = {
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    }
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code < 400:
                        return

                    meta_error = self._parse_meta_error(resp.text)
                    if self._is_meta_auth_error(meta_error):
                        last_auth_error = self._extract_meta_error(resp.text)
                        continue

                    message = self._extract_meta_error(resp.text)
                    raise HTTPException(status_code=502, detail=f"WhatsApp message send failed: {message}")

                if last_auth_error:
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            "WhatsApp message send failed: token authentication failed. "
                            "Update WHATSAPP_TOKEN (or WHATSAPP_TOKEN_FALLBACK) with a valid permanent token and restart backend. "
                            f"Meta: {last_auth_error}"
                        ),
                    )

                raise HTTPException(status_code=502, detail="WhatsApp message send failed")
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"WhatsApp API send failed: {exc}")

    def check_whatsapp_health(self, current_user: User) -> dict:
        import httpx

        if not self._can_verify_or_send(current_user):
            raise HTTPException(status_code=403, detail="You do not have permission to send invoices")

        tokens = self._get_whatsapp_tokens()
        phone_id = settings.WHATSAPP_PHONE_NUMBER_ID.strip()
        if not phone_id:
            raise HTTPException(status_code=500, detail="WHATSAPP_PHONE_NUMBER_ID is missing")
        if not tokens:
            raise HTTPException(status_code=500, detail="WHATSAPP_TOKEN is missing")

        url = f"https://graph.facebook.com/v19.0/{phone_id}"
        params = {"fields": "id,display_phone_number,verified_name"}

        try:
            with httpx.Client(timeout=10) as client:
                last_auth_error = None
                for idx, token in enumerate(tokens):
                    headers = {"Authorization": f"Bearer {token}"}
                    resp = client.get(url, headers=headers, params=params)
                    if resp.status_code < 400:
                        data = resp.json() if resp.text else {}
                        return {
                            "ok": True,
                            "phone_number_id": phone_id,
                            "display_phone_number": data.get("display_phone_number"),
                            "verified_name": data.get("verified_name"),
                            "token_source": "primary" if idx == 0 else "fallback",
                        }

                    meta_error = self._parse_meta_error(resp.text)
                    if self._is_meta_auth_error(meta_error):
                        last_auth_error = self._extract_meta_error(resp.text)
                        continue

                    message = self._extract_meta_error(resp.text)
                    raise HTTPException(status_code=502, detail=f"WhatsApp health check failed: {message}")

                if last_auth_error:
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            "WhatsApp health check failed: token authentication failed. "
                            "Rotate WHATSAPP_TOKEN (or WHATSAPP_TOKEN_FALLBACK), restart backend, then retry. "
                            f"Meta: {last_auth_error}"
                        ),
                    )
        except HTTPException:
            raise
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"WhatsApp health check failed: {exc}")

        raise HTTPException(status_code=502, detail="WhatsApp health check failed")

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
        """
        Generate a UPI QR code image (base64 PNG) for the invoice amount.
        Tries PhonePe API first; falls back to building a UPI intent URL + qrcode lib.
        Returns a base64-encoded PNG string (data:image/png;base64,...) or None.
        """
        import base64 as _b64
        import hashlib as _hashlib
        import json as _json
        import httpx
        import qrcode

        merchant_id   = settings.PHONEPE_MERCHANT_ID
        salt_key      = settings.PHONEPE_SALT_KEY
        salt_index    = settings.PHONEPE_SALT_INDEX
        is_sandbox    = settings.PHONEPE_ENV != "production"
        base_api      = (
            "https://api-preprod.phonepe.com/apis/pg-sandbox"
            if is_sandbox else
            "https://api.phonepe.com/apis/hermes"
        )

        # Helper: convert upi:// intent or any string to base64 PNG via qrcode lib
        def _make_qr_b64(data_str: str) -> str:
            img = qrcode.make(data_str)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode()

        # ── Attempt PhonePe UPI QR API ──────────────────────────────────────────
        if merchant_id and salt_key:
            try:
                txn_id  = f"QR-{(bill.invoice_number or str(bill.id)).replace('/', '-')}-{uuid.uuid4().hex[:8]}"
                payload = {
                    "merchantId":            merchant_id,
                    "merchantTransactionId": txn_id,
                    "merchantUserId":        f"MUID-{phone[-10:]}",
                    "amount":                int(round((bill.amount or 0) * 100)),  # paise
                    "mobileNumber":          phone[-10:],
                    "paymentInstrument":     {"type": "UPI_QR"},
                }
                encoded  = _b64.b64encode(_json.dumps(payload).encode()).decode()
                chk_str  = encoded + "/pg/v1/pay" + salt_key
                checksum = _hashlib.sha256(chk_str.encode()).hexdigest() + "###" + str(salt_index)
                headers  = {
                    "Content-Type":  "application/json",
                    "X-VERIFY":      checksum,
                    "X-MERCHANT-ID": merchant_id,
                }
                with httpx.Client(timeout=15) as client:
                    resp = client.post(f"{base_api}/pg/v1/pay", headers=headers, json={"request": encoded})
                    data = resp.json() if resp.text else {}
                if data.get("success"):
                    intent_url = (
                        data.get("data", {})
                        .get("instrumentResponse", {})
                        .get("intentInfo", {})
                        .get("intentUrl", "")
                    )
                    if intent_url:
                        return _make_qr_b64(intent_url)
            except Exception:
                pass  # Fall through to UPI fallback

        # ── Fallback: build a UPI intent URL from settings and generate QR ───────
        inv_settings = self.get_invoice_defaults()
        prefix = "business_" if bill.payment_type == "BUSINESS_ACCOUNT" else "personal_" if bill.payment_type == "PERSONAL_ACCOUNT" else ""
        upi_id   = inv_settings.get(f"{prefix}payment_upi_id") or inv_settings.get("payment_upi_id") or ""
        upi_name = inv_settings.get(f"{prefix}payment_account_name") or inv_settings.get("payment_account_name") or "Payment"
        static_qr = inv_settings.get(f"{prefix}payment_qr_image_url") or inv_settings.get("payment_qr_image_url") or ""
        amount   = float(bill.amount or 0)
        
        if upi_id and amount > 0:
            txn_note = f"Invoice {bill.invoice_number or bill.id}".replace("/", "-")
            upi_url  = f"upi://pay?pa={upi_id}&pn={upi_name}&am={amount:.2f}&tn={txn_note}&cu=INR"
            return _make_qr_b64(upi_url)
        elif static_qr:
            from pathlib import Path
            import httpx
            if static_qr.startswith("/static/"):
                filepath = Path(__file__).parent.parent.parent.parent / static_qr.lstrip("/")
                if filepath.exists():
                    with open(filepath, "rb") as bf:
                        import base64 as _base64
                        ext = static_qr.split(".")[-1].lower() if "." in static_qr else "png"
                        mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
                        return f"data:{mime};base64," + _base64.b64encode(bf.read()).decode()
            elif static_qr.startswith("http"):
                try:
                    with httpx.Client(timeout=10) as client:
                        resp = client.get(static_qr)
                        if resp.status_code == 200:
                            import base64 as _base64
                            mime = resp.headers.get("content-type", "image/png")
                            return f"data:{mime};base64," + _base64.b64encode(resp.content).decode()
                except:
                    pass

        return None

    def generate_payment_qr_for_new_invoice(self, payment_type: str, gst_type: str, amount: float, phone: str) -> dict:
        """
        Called BEFORE creating an invoice: resolves the amount, generates a UPI QR
        (via PhonePe or static UPI fallback) and returns display data for the
        Step-2 payment screen.
        """
        self._validate_payment_mode(payment_type, gst_type)
        inv_settings = self.get_invoice_defaults()

        if gst_type == "WITH_GST":
            gst_amount   = round(amount * 0.18, 2)
            total_amount = round(amount + gst_amount, 2)
        else:
            gst_amount   = 0.0
            total_amount = round(amount, 2)

        requires_qr = payment_type != "CASH"
        qr_b64      = None
        
        # Decide which settings to use
        prefix = "business_" if payment_type == "BUSINESS_ACCOUNT" else "personal_" if payment_type == "PERSONAL_ACCOUNT" else ""
        
        upi_id      = inv_settings.get(f"{prefix}payment_upi_id") or inv_settings.get("payment_upi_id") or ""
        upi_name    = inv_settings.get(f"{prefix}payment_account_name") or inv_settings.get("payment_account_name") or ""
        static_qr   = inv_settings.get(f"{prefix}payment_qr_image_url") or inv_settings.get("payment_qr_image_url") or ""

        if requires_qr:
            # Build a lightweight temp Bill-like object so _create_phonepe_upi_qr can work
            class _TempBill:
                invoice_number = None
                id             = 0
            _tmp = _TempBill()
            _tmp.amount = total_amount

            # Try dynamic QR (PhonePe or UPI string)
            safe_phone = phone.strip().replace("+", "").replace(" ", "")
            if len(safe_phone) == 10:
                safe_phone = "91" + safe_phone
            qr_b64 = self._create_phonepe_upi_qr(_tmp, safe_phone)

        return {
            "payment_type":  payment_type,
            "gst_type":      gst_type,
            "base_amount":   amount,
            "gst_amount":    gst_amount,
            "total_amount":  total_amount,
            "requires_qr":   requires_qr,
            "qr_image_b64":  qr_b64,            # dynamic QR (PhonePe / UPI)
            "static_qr_url": static_qr,         # admin-configured QR image URL
            "upi_id":        upi_id,
            "upi_name":      upi_name,
        }

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
        if bill.is_archived:
            raise HTTPException(status_code=400, detail="Archived invoice cannot be sent")
        if bill.invoice_status != "VERIFIED":
            raise HTTPException(status_code=400, detail="Invoice must be VERIFIED before sending")

        # Auto-create client if not already linked
        if not bill.client_id:
            client = self._ensure_client(bill, current_user)
            bill.client_id = client.id

        # Build WhatsApp document payload
        invoice_settings = self.get_invoice_defaults()
        caption = self._build_whatsapp_caption(invoice_settings)
        phone = self._normalize_indian_phone(bill.invoice_client_phone)
        filename = f"Invoice-{(bill.invoice_number or str(bill.id)).replace('/', '-')}.pdf"
        phonepe_payment_link = self._create_phonepe_payment_link(bill, phone)
        
        # Generate QR for PDF
        qr_image = None
        if bill.requires_qr and bill.payment_type != "CASH":
            qr_image = self._create_phonepe_upi_qr(bill, phone)
            
        pdf_bytes = self._build_invoice_pdf_bytes(bill, invoice_settings, qr_image)
        media_id = self._upload_whatsapp_media(pdf_bytes, filename)
        self._send_whatsapp_via_gateway(phone, media_id, caption, filename)

        bill.invoice_status = "SENT"
        bill.status = "PENDING"
        bill.whatsapp_sent = True
        self.db.commit()
        self.db.refresh(bill)

        # Auto-convert linked shop to CONVERTED once invoice is dispatched
        if bill.shop_id:
            from app.modules.shops.models import Shop
            from app.modules.projects.models import Project
            from app.core.enums import GlobalTaskStatus
            shop = self.db.query(Shop).filter(Shop.id == bill.shop_id).first()
            if shop and shop.status != GlobalTaskStatus.CONVERTED:
                shop.status = GlobalTaskStatus.CONVERTED
                self.db.commit()

                # Auto-create a Project record for this newly converted shop
                # pm_id falls back to the current billing user if no PM is assigned
                resolved_pm_id = shop.project_manager_id or current_user.id
                existing_project = self.db.query(Project).filter(
                    Project.client_id == bill.client_id
                ).first()
                if not existing_project:
                    new_project = Project(
                        name=f"{shop.name} Implementation",
                        description=f"Project auto-created on deal close. Invoice: {bill.invoice_number}.",
                        client_id=bill.client_id,
                        pm_id=resolved_pm_id,
                        status=GlobalTaskStatus.IN_PROGRESS,
                    )
                    self.db.add(new_project)
                    self.db.commit()

        invoice_file_url = None
        if base_url:
            token = self._invoice_public_token(bill.id)
            invoice_file_url = f"{base_url.rstrip('/')}/api/billing/{bill.id}/invoice-pdf?token={token}"

        print(f"--- WHATSAPP INVOICE SEND ---")
        print(f"To: {bill.invoice_client_phone}  ({bill.invoice_client_name})")
        print(f"Invoice: {bill.invoice_number}  Amount: ₹{bill.amount:,.0f}")
        print(f"Invoice File URL: {invoice_file_url}")
        print(f"----------------------------")

        if phonepe_payment_link:
            print(f"PhonePe URL: {phonepe_payment_link}")

        return {
            "bill": bill,
            "wa_url": None,
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

    def delete_bill(self, bill_id: int, current_user: User):
        # Admin only for deletion as it's sensitive
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admins can delete bills")
            
        bill = self.db.query(Bill).filter(Bill.id == bill_id).first()
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
            
        policy = self.db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
        is_hard = policy and policy.value == "HARD"

        if is_hard:
            self.db.delete(bill)
        else:
            bill.is_deleted = True
            if "-del-" not in bill.invoice_number:
                bill.invoice_number = f"{bill.invoice_number}-del-{bill.id}"

        self.db.commit()
        return {"detail": f"Bill {'permanently ' if is_hard else ''}deleted"}



