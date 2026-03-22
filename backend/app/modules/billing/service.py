from fastapi import HTTPException, Request
from app.modules.billing.models import Bill
from app.modules.billing.schemas import BillCreate, BillingWorkflowResolveRequest
from app.modules.users.models import User, UserRole
from app.core.config import settings
import datetime
from datetime import timezone
import uuid
import hmac as _hmac
import hashlib
import json
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

class BillingService:

    async def _get_setting(self, key: str, default: str = "") -> str:
        from app.modules.salary.models import AppSetting
        row = await AppSetting.find_one(AppSetting.key == key)
        return row.value if row and row.value is not None else default

    async def _set_setting(self, key: str, value: str) -> None:
        from app.modules.salary.models import AppSetting
        row = await AppSetting.find_one(AppSetting.key == key)
        if row:
            row.value = value
            await row.save()
        else:
            await AppSetting(key=key, value=value).insert()

    async def _next_invoice_number(self, gst_type: str) -> tuple:
        year = datetime.datetime.now(timezone.utc).year
        if gst_type == "WITHOUT_GST":
            seq_key = "invoice_seq_without_gst"
            series = "PINV"
            prefix = "PInv"
        else:
            seq_key = "invoice_seq_with_gst"
            series = "INV"
            prefix = "Inv"
        start = int(await self._get_setting(seq_key, "1") or "1")
        current = max(start, 1)
        while True:
            invoice_number = f"{prefix}/{year}/{current:03d}"
            exists = await Bill.find_one(Bill.invoice_number == invoice_number)
            if not exists:
                break
            current += 1
        await self._set_setting(seq_key, str(current + 1))
        return invoice_number, series, current

    async def _allowed_verifier_roles(self) -> set:
        raw = (await self._get_setting("invoice_verifier_roles", "ADMIN") or "ADMIN").strip()
        roles = {r.strip().upper() for r in raw.split(",") if r.strip()}
        return roles or {"ADMIN"}

    def _current_role_name(self, current_user: User) -> str:
        return current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)

    async def _can_verify_or_send(self, current_user: User) -> bool:
        role_name = self._current_role_name(current_user)
        return role_name in await self._allowed_verifier_roles()

    async def _allowed_invoice_creator_roles(self) -> set:
        raw = (await self._get_setting("invoice_creator_roles", "ADMIN,SALES,TELESALES,PROJECT_MANAGER_AND_SALES") or "ADMIN,SALES,TELESALES,PROJECT_MANAGER_AND_SALES").strip()
        roles = {r.strip().upper() for r in raw.split(",") if r.strip()}
        return roles or {"ADMIN", "SALES", "TELESALES", "PROJECT_MANAGER_AND_SALES"}

    async def _can_create_invoice(self, current_user: User) -> bool:
        role_name = self._current_role_name(current_user)
        return role_name in await self._allowed_invoice_creator_roles()

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

    async def get_invoice_defaults(self) -> dict:
        from app.modules.salary.models import AppSetting
        keys = ["invoice_default_amount", "personal_without_gst_default_amount", "invoice_terms_conditions", "business_payment_upi_id", "business_payment_account_name", "business_payment_qr_image_url", "business_payment_bank_name", "business_payment_account_number", "business_payment_ifsc", "business_payment_branch", "personal_payment_upi_id", "personal_payment_account_name", "personal_payment_qr_image_url", "personal_payment_bank_name", "personal_payment_account_number", "personal_payment_ifsc", "personal_payment_branch", "payment_upi_id", "payment_account_name", "payment_qr_image_url", "payment_bank_name", "payment_account_number", "payment_ifsc", "payment_branch", "company_name", "company_address", "company_header_image_details", "company_phone", "company_email", "company_gstin", "company_pan", "company_cin", "company_cst_code", "invoice_header_bg", "invoice_seq_with_gst", "invoice_seq_without_gst", "invoice_verifier_roles", "invoice_creator_roles", "whatsapp_invoice_caption"]
        rows = await AppSetting.find(AppSetting.key.in_(keys)).to_list()
        mapping = {r.key: r.value for r in rows}
        def _to_float(val, fallback):
            try:
                return float(val) if val not in (None, "") else fallback
            except:
                return fallback
        def _to_int(val, fallback):
            try:
                return int(val) if val not in (None, "") else fallback
            except:
                return fallback
        return {"invoice_default_amount": _to_float(mapping.get("invoice_default_amount"), 12000), "personal_without_gst_default_amount": _to_float(mapping.get("personal_without_gst_default_amount"), 12000), "invoice_terms_conditions": mapping.get("invoice_terms_conditions") or "• Subject to Surat Jurisdiction", "payment_upi_id": mapping.get("payment_upi_id") or "", "payment_account_name": mapping.get("payment_account_name") or "Harikrushn DigiVerse LLP", "payment_qr_image_url": mapping.get("payment_qr_image_url") or "", "payment_bank_name": mapping.get("payment_bank_name") or "", "payment_account_number": mapping.get("payment_account_number") or "", "payment_ifsc": mapping.get("payment_ifsc") or "", "payment_branch": mapping.get("payment_branch") or "", "company_name": mapping.get("company_name") or "Harikrushn DigiVerse LLP", "company_address": mapping.get("company_address") or "501-502, Silver Trade Center, near Pragati IT Park, Mota Varachha, Surat, Gujarat, India-394101", "company_header_image_details": mapping.get("company_header_image_details") or "", "company_phone": mapping.get("company_phone") or "+91 8866005029", "company_email": mapping.get("company_email") or "hetrmangukiya@gmail.com", "company_gstin": mapping.get("company_gstin") or "", "company_pan": mapping.get("company_pan") or "", "company_cin": mapping.get("company_cin") or "", "company_cst_code": mapping.get("company_cst_code") or "", "invoice_header_bg": mapping.get("invoice_header_bg") or "#2E5B82", "invoice_seq_with_gst": _to_int(mapping.get("invoice_seq_with_gst"), 1), "invoice_seq_without_gst": _to_int(mapping.get("invoice_seq_without_gst"), 1), "invoice_verifier_roles": mapping.get("invoice_verifier_roles") or "ADMIN", "invoice_creator_roles": mapping.get("invoice_creator_roles") or "ADMIN,SALES,TELESALES,PROJECT_MANAGER_AND_SALES", "whatsapp_invoice_caption": mapping.get("whatsapp_invoice_caption") or "Please find your invoice attached."}

    async def get_workflow_options(self, current_user: User) -> dict:
        inv_settings = await self.get_invoice_defaults()
        allowed_roles = sorted(await self._allowed_verifier_roles())
        allowed_creator_roles = sorted(await self._allowed_invoice_creator_roles())
        return {"payment_types": ["BUSINESS_ACCOUNT", "PERSONAL_ACCOUNT", "CASH"], "gst_types": ["WITH_GST", "WITHOUT_GST"], "constraints": {"BUSINESS_ACCOUNT": {"allowed_gst_types": ["WITH_GST"]}, "PERSONAL_ACCOUNT": {"allowed_gst_types": ["WITH_GST", "WITHOUT_GST"]}, "CASH": {"allowed_gst_types": ["WITH_GST", "WITHOUT_GST"]}}, "defaults": {"invoice_default_amount": inv_settings["invoice_default_amount"], "personal_without_gst_default_amount": inv_settings["personal_without_gst_default_amount"], "payment_type": "PERSONAL_ACCOUNT", "gst_type": "WITH_GST"}, "permissions": {"allowed_verifier_roles": allowed_roles, "can_verify_or_send": await self._can_verify_or_send(current_user), "allowed_creator_roles": allowed_creator_roles, "can_create_invoice": await self._can_create_invoice(current_user)}}

    async def resolve_workflow(self, req: BillingWorkflowResolveRequest) -> dict:
        self._validate_payment_mode(req.payment_type, req.gst_type)
        inv_settings = await self.get_invoice_defaults()
        amount_source = "client_input"
        base_amount = req.amount
        if base_amount is None:
            if req.payment_type == "PERSONAL_ACCOUNT" and req.gst_type == "WITHOUT_GST":
                base_amount = float(inv_settings.get("personal_without_gst_default_amount") or 12000)
                amount_source = "personal_without_gst_default_amount"
            else:
                base_amount = float(inv_settings.get("invoice_default_amount") or 12000)
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
        qr_available = bool(inv_settings.get("payment_qr_image_url") or inv_settings.get("payment_upi_id"))
        if requires_qr and not qr_available:
            raise HTTPException(status_code=400, detail="Payment QR/UPI is not configured in settings")
        return {"payment_type": req.payment_type, "gst_type": req.gst_type, "requires_qr": requires_qr, "amount": total_amount, "base_amount": base_amount, "gst_amount": gst_amount, "total_amount": total_amount, "amount_source": amount_source, "qr_available": qr_available, "qr_image_url": inv_settings.get("payment_qr_image_url") or None, "payment_upi_id": inv_settings.get("payment_upi_id") or None, "payment_account_name": inv_settings.get("payment_account_name") or None}

    async def get_invoice_actions(self, bill: Bill, current_user: User) -> dict:
        can_verify = await self._can_verify_or_send(current_user) and not bool(bill.is_archived) and bill.invoice_status in {"DRAFT", "PENDING_VERIFICATION"}
        can_send_whatsapp = await self._can_verify_or_send(current_user) and not bool(bill.is_archived) and bill.invoice_status == "VERIFIED"
        can_archive = self._can_archive_invoice(current_user, bill) and not bool(bill.is_archived)
        can_unarchive = self._can_archive_invoice(current_user, bill) and bool(bill.is_archived)
        can_delete_archived = self._can_archive_invoice(current_user, bill) and bool(bill.is_archived)
        return {"can_verify": can_verify, "can_send_whatsapp": can_send_whatsapp, "can_archive": can_archive, "can_unarchive": can_unarchive, "can_delete_archived": can_delete_archived, "allowed_verifier_roles": sorted(await self._allowed_verifier_roles())}

    async def save_invoice_settings(self, payload: dict) -> dict:
        from app.modules.salary.models import AppSetting
        allowed = {"invoice_default_amount", "personal_without_gst_default_amount", "invoice_terms_conditions", "business_payment_upi_id", "business_payment_account_name", "business_payment_qr_image_url", "business_payment_bank_name", "business_payment_account_number", "business_payment_ifsc", "business_payment_branch", "personal_payment_upi_id", "personal_payment_account_name", "personal_payment_qr_image_url", "personal_payment_bank_name", "personal_payment_account_number", "personal_payment_ifsc", "personal_payment_branch", "payment_upi_id", "payment_account_name", "payment_qr_image_url", "payment_bank_name", "payment_account_number", "payment_ifsc", "payment_branch", "company_name", "company_address", "company_header_image_details", "company_phone", "company_email", "company_gstin", "company_pan", "company_cin", "company_cst_code", "invoice_header_bg", "invoice_seq_with_gst", "invoice_seq_without_gst", "invoice_verifier_roles", "invoice_creator_roles", "whatsapp_invoice_caption"}
        for key, value in payload.items():
            if key not in allowed:
                continue
            await self._set_setting(key, str(value))
        return await self.get_invoice_defaults()

    async def create_invoice(self, bill_in: BillCreate, current_user: User) -> Bill:
        self._validate_payment_mode(bill_in.payment_type, bill_in.gst_type)
        if not await self._can_create_invoice(current_user):
            raise HTTPException(status_code=403, detail="You do not have permission to create invoices")
        if bill_in.invoice_client_phone:
            active_bill = await Bill.find_one(Bill.invoice_client_phone == bill_in.invoice_client_phone.strip(), Bill.is_archived == False, Bill.is_deleted == False)
            if active_bill:
                raise HTTPException(status_code=400, detail="An active invoice already exists for this client's phone number.")
        resolved = await self.resolve_workflow(BillingWorkflowResolveRequest(payment_type=bill_in.payment_type, gst_type=bill_in.gst_type, amount=bill_in.amount))
        amount = resolved["total_amount"]
        requires_qr = resolved["requires_qr"]
        invoice_number, invoice_series, invoice_sequence = await self._next_invoice_number(bill_in.gst_type)
        from app.modules.clients.models import Client
        existing_client = None
        if bill_in.invoice_client_phone:
            existing_client = await Client.find_one(Client.phone == bill_in.invoice_client_phone.strip())
        if existing_client and current_user.role != UserRole.ADMIN:
            can_use = (existing_client.owner_id == current_user.id or existing_client.pm_id == current_user.id or existing_client.referred_by_id == current_user.id)
            if not can_use:
                raise HTTPException(status_code=403, detail="You can create invoice only for your own client or a new client")
        db_bill = Bill(shop_id=bill_in.shop_id, client_id=existing_client.id if existing_client else None, invoice_client_name=bill_in.invoice_client_name, invoice_client_phone=bill_in.invoice_client_phone, invoice_client_email=bill_in.invoice_client_email, invoice_client_address=bill_in.invoice_client_address, invoice_client_org=bill_in.invoice_client_org, amount=amount, payment_type=bill_in.payment_type, gst_type=bill_in.gst_type, invoice_series=invoice_series, invoice_sequence=invoice_sequence, requires_qr=requires_qr, service_description=bill_in.service_description, invoice_number=invoice_number, invoice_status="PENDING_VERIFICATION", status="PENDING", created_by_id=current_user.id)
        await db_bill.insert()
        return db_bill

    async def get_bill(self, bill_id: str):
        from app.modules.salary.models import AppSetting
        policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
        if not policy or policy.value == "SOFT":
            return await Bill.find_one(Bill.id == bill_id, Bill.is_deleted == False)
        return await Bill.find_one(Bill.id == bill_id)

    async def get_all_bills(self, current_user: User, skip: int = 0, limit: int = 200, status_filter=None, archived="ACTIVE", payment_type=None, gst_type=None, search=None):
        from app.modules.salary.models import AppSetting
        policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
        query_filter = []
        if not policy or policy.value == "SOFT":
            query_filter.append(Bill.is_deleted == False)
        if current_user.role != UserRole.ADMIN:
            query_filter.append(Bill.created_by_id == current_user.id)
        archived_mode = (archived or "ACTIVE").upper()
        if archived_mode == "ARCHIVED":
            query_filter.append(Bill.is_archived == True)
        elif archived_mode != "ALL":
            query_filter.append(Bill.is_archived == False)
        if status_filter and status_filter.upper() != "ALL":
            query_filter.append(Bill.invoice_status == status_filter.upper())
        if payment_type and payment_type.upper() != "ALL":
            query_filter.append(Bill.payment_type == payment_type.upper())
        if gst_type and gst_type.upper() != "ALL":
            query_filter.append(Bill.gst_type == gst_type.upper())
        bills = await Bill.find(*query_filter).sort(-Bill.created_at).skip(skip).limit(limit).to_list()
        if search:
            token = search.strip().lower()
            bills = [b for b in bills if token in (b.invoice_number or "").lower() or token in (b.invoice_client_name or "").lower() or token in (b.invoice_client_phone or "").lower() or token in (b.invoice_client_org or "").lower()]
        return bills

    async def verify_invoice(self, bill_id: str, current_user: User) -> Bill:
        if not await self._can_verify_or_send(current_user):
            raise HTTPException(status_code=403, detail="You do not have permission to verify invoices")
        bill = await self.get_bill(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if bill.is_archived:
            raise HTTPException(status_code=400, detail="Archived invoice cannot be verified")
        if bill.invoice_status not in ("PENDING_VERIFICATION", "DRAFT"):
            raise HTTPException(status_code=400, detail=f"Invoice cannot be verified from status '{bill.invoice_status}'")
        bill.invoice_status = "VERIFIED"
        bill.verified_by_id = current_user.id
        bill.verified_at = datetime.datetime.now(timezone.utc)
        await bill.save()
        return bill

    async def archive_invoice(self, bill_id: str, current_user: User) -> Bill:
        bill = await self.get_bill(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if not self._can_archive_invoice(current_user, bill):
            raise HTTPException(status_code=403, detail="You do not have permission to archive this invoice")
        if bill.is_archived:
            return bill
        bill.is_archived = True
        await bill.save()
        return bill

    async def unarchive_invoice(self, bill_id: str, current_user: User) -> Bill:
        bill = await self.get_bill(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if not self._can_archive_invoice(current_user, bill):
            raise HTTPException(status_code=403, detail="You do not have permission to unarchive this invoice")
        if not bill.is_archived:
            return bill
        bill.is_archived = False
        await bill.save()
        return bill

    async def archive_invoices_bulk(self, bill_ids: list, current_user: User) -> dict:
        ids = sorted({int(i) for i in (bill_ids or []) if str(i).strip()})
        if not ids:
            raise HTTPException(status_code=400, detail="No invoice ids provided")
        rows = await Bill.find(Bill.id.in_(ids), Bill.is_deleted == False).to_list()
        updated = 0
        for bill in rows:
            if self._can_archive_invoice(current_user, bill) and not bool(bill.is_archived):
                bill.is_archived = True
                await bill.save()
                updated += 1
        return {"requested": len(ids), "matched": len(rows), "archived": updated}

    async def delete_archived_invoice(self, bill_id: str, current_user: User) -> dict:
        bill = await self.get_bill(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if not self._can_archive_invoice(current_user, bill):
            raise HTTPException(status_code=403, detail="You do not have permission to delete this invoice")
        if not bill.is_archived:
            raise HTTPException(status_code=400, detail="Only archived invoices can be deleted")
        from app.modules.salary.models import AppSetting
        policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
        is_hard = bool(policy and policy.value == "HARD")
        if is_hard:
            await bill.delete()
        else:
            bill.is_deleted = True
            if "-del-" not in (bill.invoice_number or ""):
                bill.invoice_number = f"{bill.invoice_number}-del-{bill.id}"
            await bill.save()
        return {"success": True, "deleted": 1}

    async def delete_archived_invoices_bulk(self, bill_ids: list, current_user: User) -> dict:
        ids = sorted({int(i) for i in (bill_ids or []) if str(i).strip()})
        if not ids:
            raise HTTPException(status_code=400, detail="No invoice ids provided")
        from app.modules.salary.models import AppSetting
        rows = await Bill.find(Bill.id.in_(ids), Bill.is_deleted == False).to_list()
        policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
        is_hard = bool(policy and policy.value == "HARD")
        deleted = 0
        for bill in rows:
            if not self._can_archive_invoice(current_user, bill):
                continue
            if not bill.is_archived:
                continue
            if is_hard:
                await bill.delete()
            else:
                bill.is_deleted = True
                if "-del-" not in (bill.invoice_number or ""):
                    bill.invoice_number = f"{bill.invoice_number}-del-{bill.id}"
                await bill.save()
            deleted += 1
        return {"requested": len(ids), "matched": len(rows), "deleted": deleted}

    @staticmethod
    def _invoice_public_token(bill_id: str) -> str:
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

    @staticmethod
    def _build_invoice_pdf_bytes(bill: Bill, invoice_settings: dict, qr_image_b64: str = None) -> bytes:
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
        c.drawString(x, y, (bill.service_description or "Software – Annual Subscription")[:80])
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
        if qr_image_b64:
            try:
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

    async def _ensure_client(self, bill: Bill, current_user: User):
        from app.modules.clients.models import Client
        existing = None
        if bill.invoice_client_phone:
            existing = await Client.find_one(Client.phone == bill.invoice_client_phone)
        if bill.invoice_client_email and not existing:
            existing = await Client.find_one(Client.email == bill.invoice_client_email)
        if existing:
            return existing
        email = bill.invoice_client_email or f"client_{uuid.uuid4().hex[:8]}@placeholder.com"
        client = Client(name=bill.invoice_client_name, email=email, phone=bill.invoice_client_phone, organization=bill.invoice_client_org, address=bill.invoice_client_address, owner_id=current_user.id, is_active=True)
        await client.insert()
        return client

    async def send_whatsapp_invoice(self, bill_id: str, current_user: User, base_url: str = "") -> dict:
        if not await self._can_verify_or_send(current_user):
            raise HTTPException(status_code=403, detail="You do not have permission to send invoices")
        bill = await self.get_bill(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if bill.is_archived:
            raise HTTPException(status_code=400, detail="Archived invoice cannot be sent")
        if bill.invoice_status != "VERIFIED":
            raise HTTPException(status_code=400, detail="Invoice must be VERIFIED before sending")
        if not bill.client_id:
            client = await self._ensure_client(bill, current_user)
            bill.client_id = client.id
        invoice_settings = await self.get_invoice_defaults()
        caption = self._build_whatsapp_caption(invoice_settings)
        phone = self._normalize_indian_phone(bill.invoice_client_phone)
        filename = f"Invoice-{(bill.invoice_number or str(bill.id)).replace('/', '-')}.pdf"
        qr_image = None
        if bill.requires_qr and bill.payment_type != "CASH":
            qr_image = await self._create_phonepe_upi_qr(bill, phone)
        pdf_bytes = self._build_invoice_pdf_bytes(bill, invoice_settings, qr_image)
        media_id = self._upload_whatsapp_media(pdf_bytes, filename)
        self._send_whatsapp_via_gateway(phone, media_id, caption, filename)
        bill.invoice_status = "SENT"
        bill.status = "PENDING"
        bill.whatsapp_sent = True
        await bill.save()
        if bill.shop_id:
            from app.modules.shops.models import Shop
            from app.modules.projects.models import Project
            from app.core.enums import GlobalTaskStatus
            shop = await Shop.find_one(Shop.id == bill.shop_id)
            if shop and shop.status != GlobalTaskStatus.CONVERTED:
                shop.status = GlobalTaskStatus.CONVERTED
                await shop.save()
                resolved_pm_id = shop.project_manager_id or current_user.id
                existing_project = await Project.find_one(Project.client_id == bill.client_id)
                if not existing_project:
                    new_project = Project(name=f"{shop.name} Implementation", description=f"Project auto-created on deal close. Invoice: {bill.invoice_number}.", client_id=bill.client_id, pm_id=resolved_pm_id, status=GlobalTaskStatus.IN_PROGRESS)
                    await new_project.insert()
        return {"bill": bill, "wa_url": None, "phonepe_payment_link": None}

    async def delete_bill(self, bill_id: str, current_user: User):
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admins can delete bills")
        bill = await Bill.find_one(Bill.id == bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        from app.modules.salary.models import AppSetting
        policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
        is_hard = policy and policy.value == "HARD"
        if is_hard:
            await bill.delete()
        else:
            bill.is_deleted = True
            if "-del-" not in (bill.invoice_number or ""):
                bill.invoice_number = f"{bill.invoice_number}-del-{bill.id}"
            await bill.save()
        return {"detail": f"Bill deleted"}

    async def _create_phonepe_upi_qr(self, bill, phone: str):
        import base64 as _b64
        import hashlib as _hashlib
        import json as _json
        import httpx
        import qrcode
        merchant_id = settings.PHONEPE_MERCHANT_ID
        salt_key = settings.PHONEPE_SALT_KEY
        salt_index = settings.PHONEPE_SALT_INDEX
        is_sandbox = settings.PHONEPE_ENV != "production"
        base_api = "https://api-preprod.phonepe.com/apis/pg-sandbox" if is_sandbox else "https://api.phonepe.com/apis/hermes"
        def _make_qr_b64(data_str: str) -> str:
            img = qrcode.make(data_str)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode()
        inv_settings = await self.get_invoice_defaults()
        prefix = "business_" if bill.payment_type == "BUSINESS_ACCOUNT" else "personal_" if bill.payment_type == "PERSONAL_ACCOUNT" else ""
        upi_id = inv_settings.get(f"{prefix}payment_upi_id") or inv_settings.get("payment_upi_id") or ""
        upi_name = inv_settings.get(f"{prefix}payment_account_name") or inv_settings.get("payment_account_name") or "Payment"
        amount = float(bill.amount or 0)
        if upi_id and amount > 0:
            txn_note = f"Invoice {bill.invoice_number or bill.id}".replace("/", "-")
            upi_url = f"upi://pay?pa={upi_id}&pn={upi_name}&am={amount:.2f}&tn={txn_note}&cu=INR"
            return _make_qr_b64(upi_url)
        return None

    def _upload_whatsapp_media(self, pdf_bytes: bytes, filename: str) -> str:
        import httpx
        tokens = self._get_whatsapp_tokens()
        phone_id = settings.WHATSAPP_PHONE_NUMBER_ID.strip()
        if not tokens or not phone_id:
            raise HTTPException(status_code=500, detail="WhatsApp API is not configured")
        upload_url = f"https://graph.facebook.com/v19.0/{phone_id}/media"
        form_data = {"messaging_product": "whatsapp", "type": "application/pdf"}
        files = {"file": (filename, pdf_bytes, "application/pdf")}
        try:
            with httpx.Client(timeout=30) as client:
                for token in tokens:
                    headers = {"Authorization": f"Bearer {token}"}
                    resp = client.post(upload_url, headers=headers, data=form_data, files=files)
                    if resp.status_code < 400:
                        media_id = (resp.json() or {}).get("id")
                        if not media_id:
                            raise HTTPException(status_code=502, detail="WhatsApp media upload failed: missing media id")
                        return media_id
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
        payload = {"messaging_product": "whatsapp", "to": phone, "type": "document", "document": {"id": media_id, "caption": caption, "filename": filename}}
        try:
            with httpx.Client(timeout=10) as client:
                for token in tokens:
                    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code < 400:
                        return
                raise HTTPException(status_code=502, detail="WhatsApp message send failed")
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"WhatsApp API send failed: {exc}")

    def _get_whatsapp_tokens(self) -> list:
        tokens = []
        primary = (settings.WHATSAPP_TOKEN or "").strip()
        fallback = (settings.WHATSAPP_TOKEN_FALLBACK or "").strip()
        for token in (primary, fallback):
            if token and token not in tokens:
                tokens.append(token)
        return tokens

    async def generate_bill_and_convert(self, bill_in, current_user, request):
        return await self.create_invoice(bill_in, current_user)

    async def confirm_bill(self, bill_id: str, current_user: User, request):
        return await self.verify_invoice(bill_id, current_user)
