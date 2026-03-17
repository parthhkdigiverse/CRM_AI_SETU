# backend/app/modules/billing/router.py
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
import shutil
import uuid
from pathlib import Path
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.shops.models import Shop
from app.modules.feedback.models import Feedback
from app.modules.clients.models import Client
from app.modules.billing.schemas import (
  BillCreate,
  BillRead,
  BillingWorkflowResolveRequest,
  BillingWorkflowResolveResponse,
  BillingInvoiceActionResponse,
)
from app.modules.billing.service import BillingService

router = APIRouter()

# Staff who can create / view invoices
staff_access = RoleChecker([
    UserRole.ADMIN,
    UserRole.SALES,
    UserRole.TELESALES,
    UserRole.PROJECT_MANAGER,
  UserRole.PROJECT_MANAGER_AND_SALES,
])

# Only admin
admin_only = RoleChecker([UserRole.ADMIN])


# ──────────────────── Settings ────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent.parent.parent
QR_UPLOAD_DIR = BASE_DIR / "static" / "uploads" / "qrs"
QR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/settings/upload-qr")
async def upload_qr_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
) -> Any:
    """Uploads a QR image and returns its URL."""
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
    filename = f"qr_{uuid.uuid4().hex}.{ext}"
    file_path = QR_UPLOAD_DIR / filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"url": f"/static/uploads/qrs/{filename}"}


@router.get("/settings")
def get_invoice_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
) -> Any:
    """Return default invoice amount and payment QR/UPI configuration."""
    return BillingService(db).get_invoice_defaults()


@router.put("/settings")
def update_invoice_settings(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
) -> Any:
    """Admin updates invoice defaults and payment QR settings."""
    return BillingService(db).save_invoice_settings(payload)


# ──────────────────── Invoice CRUD ────────────────────────────────────────────

@router.get("/workflow/options")
def get_invoice_workflow_options(
  db: Session = Depends(get_db),
  current_user: User = Depends(staff_access),
) -> Any:
  """Return payment type/GST constraints, defaults and role permissions."""
  return BillingService(db).get_workflow_options(current_user)


@router.get("/autofill-sources")
def get_billing_autofill_sources(
  source: str,
  db: Session = Depends(get_db),
  current_user: User = Depends(staff_access),
) -> Any:
  source_key = (source or "").strip().lower()
  if source_key not in {"visit", "feedback"}:
    raise HTTPException(status_code=400, detail="source must be 'visit' or 'feedback'")

  role = current_user.role

  def _client_scope_filter(query):
    if role == UserRole.ADMIN:
      return query
    if role in (UserRole.SALES, UserRole.TELESALES):
      return query.filter(Client.owner_id == current_user.id)
    if role == UserRole.PROJECT_MANAGER:
      return query.filter(Client.pm_id == current_user.id)
    return query.filter(
      (Client.owner_id == current_user.id)
      | (Client.pm_id == current_user.id)
      | (Client.referred_by_id == current_user.id)
    )

  if source_key == "visit":
    q = db.query(Shop).filter(Shop.is_deleted == False)
    if role != UserRole.ADMIN:
      q = q.filter(Shop.owner_id == current_user.id)
    shops = q.order_by(Shop.id.desc()).limit(250).all()
    return [
      {
        "id": s.id,
        "name": s.contact_person or s.name or "",
        "phone": s.phone or "",
        "email": s.email or "",
        "org": s.name or "",
        "address": s.address or "",
        "label": (s.contact_person or s.name or "Shop") + ((f" · {s.name}") if s.contact_person and s.name else ""),
      }
      for s in shops
    ]

  q = db.query(Feedback, Client).join(Client, Client.id == Feedback.client_id, isouter=True)
  q = q.filter(Feedback.is_deleted == False)
  q = _client_scope_filter(q)
  rows = q.order_by(Feedback.created_at.desc()).limit(250).all()
  return [
    {
      "id": f.id,
      "name": f.client_name or (c.name if c else ""),
      "phone": (c.phone if c else "") or "",
      "email": (c.email if c else "") or "",
      "org": (c.organization if c else "") or "",
      "address": (c.address if c else "") or "",
      "label": f.client_name or (c.name if c else "Feedback"),
    }
    for f, c in rows
  ]


@router.post("/workflow/resolve", response_model=BillingWorkflowResolveResponse)
def resolve_invoice_workflow(
  payload: BillingWorkflowResolveRequest,
  db: Session = Depends(get_db),
  current_user: User = Depends(staff_access),
) -> Any:
  """Resolve amount, QR requirement and payable metadata for selected payment/GST type."""
  return BillingService(db).resolve_workflow(payload)


@router.post("/generate-qr")
def generate_payment_qr(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
) -> Any:
    """
    Step 2 of the new invoice wizard.
    Resolves the total amount, generates a PhonePe UPI QR (or static fallback),
    and returns display data. No invoice is created yet.
    """
    payment_type = payload.get("payment_type", "")
    gst_type     = payload.get("gst_type", "")
    amount       = float(payload.get("amount") or 0)
    phone        = str(payload.get("phone") or "9999999999")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    return BillingService(db).generate_payment_qr_for_new_invoice(
        payment_type=payment_type,
        gst_type=gst_type,
        amount=amount,
        phone=phone,
    )


@router.post("/phonepe-callback")
async def phonepe_payment_callback(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """
    PhonePe posts payment status here after redirect.
    Validates HMAC signature, logs the event, and returns 200.
    Note: In production, use this to auto-verify invoices.
    """
    import hashlib, hmac as _hmac, base64 as _b64, json as _json
    from app.core.config import settings

    body = await request.body()
    x_verify = request.headers.get("X-VERIFY", "")
    salt_key  = settings.PHONEPE_SALT_KEY
    salt_idx  = settings.PHONEPE_SALT_INDEX

    # Validate signature: sha256(base64_response + salt_key) + "###" + salt_index
    try:
        data_b64 = _json.loads(body).get("response", "")
        expected_hash = hashlib.sha256((data_b64 + salt_key).encode()).hexdigest()
        expected_verify = f"{expected_hash}###{salt_idx}"
        sig_ok = _hmac.compare_digest(x_verify, expected_verify)
    except Exception:
        sig_ok = False

    if not sig_ok:
        print("[PhonePe Callback] Signature mismatch — ignoring")
        return {"status": "ignored"}

    try:
        decoded = _json.loads(_b64.b64decode(data_b64).decode())
        txn_id  = decoded.get("data", {}).get("merchantTransactionId", "")
        code    = decoded.get("code", "")
        print(f"[PhonePe Callback] txn={txn_id}  code={code}  ok={sig_ok}")
    except Exception as exc:
        print(f"[PhonePe Callback] Parse error: {exc}")

    return {"status": "received"}


@router.post("/", response_model=BillRead)
def create_invoice(
    bill_in: BillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
) -> Any:
    """Create a new invoice (status: PENDING_VERIFICATION)."""
    return BillingService(db).create_invoice(bill_in, current_user)


@router.get("/", response_model=List[BillRead])
def list_invoices(
    skip: int = 0,
    limit: int = 200,
    status_filter: Optional[str] = None,
    archived: Optional[str] = "ACTIVE",
    payment_type: Optional[str] = None,
    gst_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
) -> Any:
  """List invoices with server-side filters and role-based data scope."""
  return BillingService(db).get_all_bills(
    current_user,
    skip=skip,
    limit=limit,
    status_filter=status_filter,
    archived=archived,
    payment_type=payment_type,
    gst_type=gst_type,
    search=search,
  )


@router.get("/whatsapp-health")
def whatsapp_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
) -> Any:
    """Validate WhatsApp token + phone number configuration with Meta Graph API."""
    return BillingService(db).check_whatsapp_health(current_user)


@router.get("/{bill_id}", response_model=BillRead)
def get_invoice(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
) -> Any:
    svc = BillingService(db)
    bill = svc.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return bill


@router.get("/{bill_id}/actions", response_model=BillingInvoiceActionResponse)
def get_invoice_actions(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
) -> Any:
    """Return user-specific allowed actions for an invoice."""
    svc = BillingService(db)
    bill = svc.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return svc.get_invoice_actions(bill, current_user)


# ──────────────────── Workflow ─────────────────────────────────────────────────

@router.patch("/{bill_id}/verify", response_model=BillRead)
def verify_invoice(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
) -> Any:
    """Verify the invoice (allowed roles are controlled in billing settings)."""
    return BillingService(db).verify_invoice(bill_id, current_user)


@router.patch("/{bill_id}/archive", response_model=BillRead)
def archive_invoice(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
 ) -> Any:
    """Archive a single invoice."""
    return BillingService(db).archive_invoice(bill_id, current_user)


@router.patch("/{bill_id}/unarchive", response_model=BillRead)
def unarchive_invoice(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
 ) -> Any:
    """Restore a single archived invoice."""
    return BillingService(db).unarchive_invoice(bill_id, current_user)


@router.patch("/archive/bulk")
def archive_invoices_bulk(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
 ) -> Any:
    """Archive multiple invoices at once from active list."""
    ids = payload.get("ids") if isinstance(payload, dict) else []
    return BillingService(db).archive_invoices_bulk(ids or [], current_user)


@router.delete("/{bill_id}/archive-delete")
def delete_archived_invoice(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
 ) -> Any:
    """Delete an archived invoice (soft/hard based on delete_policy)."""
    return BillingService(db).delete_archived_invoice(bill_id, current_user)


@router.post("/archive/delete-bulk")
def delete_archived_invoices_bulk(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
 ) -> Any:
    """Delete multiple archived invoices."""
    ids = payload.get("ids") if isinstance(payload, dict) else []
    return BillingService(db).delete_archived_invoices_bulk(ids or [], current_user)


@router.post("/{bill_id}/send-whatsapp")
async def send_invoice_whatsapp(
    bill_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
) -> Any:
    """
    Admin sends verified invoice to client via WhatsApp.
    Auto-creates client if not already in the system.
    Returns the WhatsApp URL to open.
    """
    # Assuming FastAPI Request has `.url` which is a starlette.datastructures.URL object
    # We want the base_url, e.g. "http://127.0.0.1:8000/"
    base_url = str(request.base_url)
    result = await BillingService(db).send_whatsapp_invoice(
        bill_id=bill_id, 
        current_user=current_user,
        base_url=base_url
    )
    bill = result["bill"]
    wa_url = result["wa_url"]
    phonepe_payment_link = result.get("phonepe_payment_link")
    return {
        "success": True,
        "wa_url": wa_url,
        "phonepe_payment_link": phonepe_payment_link,
        "invoice_status": bill.invoice_status,
        "client_id": bill.client_id,
    }



# ──────────────────── Printable Invoice HTML ──────────────────────────────────

@router.get("/{bill_id}/invoice-html", response_class=HTMLResponse)
def get_invoice_html(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
):
    """Return a print-ready A4 HTML invoice page."""
    svc = BillingService(db)
    bill = svc.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Invoice not found")
    settings = svc.get_invoice_defaults()
    html = _build_invoice_html(bill, settings)
    return HTMLResponse(content=html)


def _build_invoice_html(bill, settings: dict) -> str:
    from datetime import datetime, timezone

    company_name    = settings.get("company_name")    or "Harikrushn DigiVerse LLP"
    company_address = settings.get("company_address") or ""
    company_phone   = settings.get("company_phone")   or ""
    company_email   = settings.get("company_email")   or ""
    company_gstin   = settings.get("company_gstin")   or ""
    company_pan     = settings.get("company_pan")     or ""
    company_cin     = settings.get("company_cin")     or ""
    company_cst     = settings.get("company_cst_code") or ""
    
    # Resolve payment details based on bill payment type
    prefix = "business_" if bill.payment_type == "BUSINESS_ACCOUNT" else "personal_" if bill.payment_type == "PERSONAL_ACCOUNT" else ""
    
    upi_id          = settings.get(f"{prefix}payment_upi_id") or settings.get("payment_upi_id") or ""
    upi_name        = settings.get(f"{prefix}payment_account_name") or settings.get("payment_account_name") or company_name
    qr_img_url      = settings.get(f"{prefix}payment_qr_image_url") or settings.get("payment_qr_image_url") or ""
    bank_name       = settings.get(f"{prefix}payment_bank_name") or settings.get("payment_bank_name") or ""
    bank_account_no = settings.get(f"{prefix}payment_account_number") or settings.get("payment_account_number") or ""
    bank_ifsc       = settings.get(f"{prefix}payment_ifsc") or settings.get("payment_ifsc") or ""
    bank_branch     = settings.get(f"{prefix}payment_branch") or settings.get("payment_branch") or ""

    header_bg = settings.get("invoice_header_bg") or "#2E5B82"

    def _is_dark_hex(hex_color: str) -> bool:
      val = (hex_color or "").strip().lstrip("#")
      if len(val) != 6:
        return True
      try:
        r = int(val[0:2], 16)
        g = int(val[2:4], 16)
        b = int(val[4:6], 16)
      except ValueError:
        return True
      luma = (0.2126 * r) + (0.7152 * g) + (0.0722 * b)
      return luma < 140

    header_is_dark = _is_dark_hex(header_bg)
    header_text = "#f8fafc" if header_is_dark else "#0f172a"
    header_sub_text = "#cbd5e1" if header_is_dark else "#334155"
    logo_src = "/frontend/images/white%20logo.png" if header_is_dark else "/frontend/images/logo.png"

    _dt = bill.created_at if bill.created_at else datetime.now(timezone.utc)
    invoice_date = _dt.strftime("%d %b %Y, %I:%M %p").lstrip("0")

    client_name    = bill.invoice_client_name    or "—"
    client_phone   = bill.invoice_client_phone   or "—"
    client_email   = bill.invoice_client_email   or ""
    client_address = bill.invoice_client_address or ""
    client_org     = bill.invoice_client_org     or ""

    service_desc   = bill.service_description or "CRM AI SETU Software – Annual Subscription"
    amount         = bill.amount or 0.0

    is_with_gst = (bill.gst_type or "WITH_GST") == "WITH_GST"

    # Amount in bill.amount is treated as total payable amount.
    # For WITH_GST invoices, split into taxable + 9% CGST + 9% SGST.
    if is_with_gst:
      subtotal = round(amount / 1.18, 2)
      cgst_rate = 9
      sgst_rate = 9
      cgst_amt = round(subtotal * cgst_rate / 100, 2)
      sgst_amt = round(subtotal * sgst_rate / 100, 2)
    else:
      subtotal = amount
      cgst_rate = 0
      sgst_rate = 0
      cgst_amt = 0.0
      sgst_amt = 0.0

    total_tax      = cgst_amt + sgst_amt
    total_before_round = subtotal + total_tax
    rounded_total  = round(total_before_round)
    round_off      = round(rounded_total - total_before_round, 2)

    if bill.payment_type == "BUSINESS_ACCOUNT":
        payment_type_label = "Bank Account"
    elif bill.payment_type == "PERSONAL_ACCOUNT":
        if is_with_gst:
            payment_type_label = "Bank Account"
        else:
            payment_type_label = "Personal Account"
    elif bill.payment_type == "CASH":
        payment_type_label = "Cash"
    else:
        payment_type_label = bill.payment_type or "-"
    gst_type_label = "With GST" if is_with_gst else "Without GST"

    status_label = {
        "DRAFT":                "Draft",
        "PENDING_VERIFICATION": "Pending",
        "VERIFIED":             "Verified",
        "SENT":                 "Paid",
    }.get(bill.invoice_status, bill.invoice_status)

    company_ids = []
    if company_gstin: company_ids.append(f"GSTIN: {company_gstin}")
    if company_pan: company_ids.append(f"PAN: {company_pan}")
    if company_cin: company_ids.append(f"LLPIN: {company_cin}")
    company_ids_str = " | ".join(company_ids)
    
    item_rate = subtotal if is_with_gst else rounded_total
    
    if is_with_gst:
        tax_cols_th = '<th style="width:80px;text-align:right;">Discount</th><th style="width:90px;text-align:right;">Taxable</th>'
        tax_cols_td = f'<td style="text-align:right;">-</td><td style="text-align:right;font-weight:700;">₹{subtotal:,.2f}</td>'
        summary_html = f"""
        <tr><td>Total Before Tax</td><td>₹{subtotal:,.2f}</td></tr>
        <tr><td>CGST ({cgst_rate}%)</td><td>₹{cgst_amt:,.2f}</td></tr>
        <tr><td>SGST ({sgst_rate}%)</td><td>₹{sgst_amt:,.2f}</td></tr>
        <tr><td>Round Off</td><td>₹{round_off:,.2f}</td></tr>
        <tr class="grand-row"><td>Total Amount</td><td>₹{rounded_total:,.2f}</td></tr>
        """
    else:
        tax_cols_th = ''
        tax_cols_td = ''
        summary_html = f"""
        <tr class="grand-row"><td>Total Amount</td><td>₹{rounded_total:,.2f}</td></tr>
        """
        
    inv_terms = settings.get("invoice_terms_conditions") or "• Subject to Surat Jurisdiction"
    terms_html = "<br>".join([line for line in inv_terms.split("\\n") if line.strip()])

    # ── Amount in words ──────────────────────────────────────────────────────
    def _num_to_words(n: int) -> str:
        if n == 0:
            return "Zero"
        ones = ["", "One","Two","Three","Four","Five","Six","Seven","Eight","Nine",
                "Ten","Eleven","Twelve","Thirteen","Fourteen","Fifteen","Sixteen",
                "Seventeen","Eighteen","Nineteen"]
        tens = ["","","Twenty","Thirty","Forty","Fifty","Sixty","Seventy","Eighty","Ninety"]
        def _below_1000(num):
            if num == 0: return ""
            if num < 20: return ones[num]
            if num < 100: return tens[num // 10] + (" " + ones[num % 10] if num % 10 else "")
            return ones[num // 100] + " Hundred" + (" " + _below_1000(num % 100) if num % 100 else "")
        parts = []
        cr = n // 10000000; n %= 10000000
        lk = n // 100000;   n %= 100000
        th = n // 1000;     n %= 1000
        if cr: parts.append(_below_1000(cr) + " Crore")
        if lk: parts.append(_below_1000(lk) + " Lakh")
        if th: parts.append(_below_1000(th) + " Thousand")
        if n:  parts.append(_below_1000(n))
        return " ".join(parts)

    amount_words = _num_to_words(int(rounded_total)) + " Only"

    # Conditional rendering helpers
    def opt_row(label, val):
        return f'<tr><td class="lbl">{label}</td><td>{val}</td></tr>' if val else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Tax Invoice — {bill.invoice_number}</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box;}}
  @page{{size:A4;margin:0;}}
  :root{{--invoice-accent:{header_bg};--invoice-accent-text:{header_text};--invoice-light-border:#d1d5db;}}
  body{{font-family:Arial,Helvetica,sans-serif;background:#f4f6f9;font-size:14px;color:#111;}}
  .wrapper{{width:210mm;min-height:297mm;margin:0 auto;background:#fff;}}
  /* ── print bar ── */
  .print-bar{{background:var(--invoice-accent);padding:10px 18px;display:flex;gap:10px;align-items:center;}}
  .print-bar button{{border:none;padding:8px 22px;font-size:13px;font-weight:700;border-radius:6px;cursor:pointer;}}
  .btn-print{{background:var(--invoice-accent);color:#fff;}}
  .btn-close{{background:var(--invoice-accent);color:#fff;}}
  @media print{{.print-bar{{display:none!important;}}body{{background:#fff;-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;}}}}
  /* ── invoice page ── */
  .inv-page{{padding:4mm 4mm 4mm 4mm;}}
  /* company header */
  .co-header{{display:flex;justify-content:space-between;align-items:flex-start;
    border:1px solid #d1d5db;padding:8px 10px;margin-bottom:8px;}}
  .co-left .co-name{{font-size:17px;font-weight:900;letter-spacing:.2px;}}
  .co-left .co-sub{{font-size:11.5px;margin-top:3px;max-width:420px;line-height:1.5;}}
  .co-right{{text-align:right;}}
  .co-right .ti-label{{font-size:16px;font-weight:900;letter-spacing:.6px;}}
  .co-right table td{{font-size:12px;padding:1px 4px;}}
  .co-right table td:first-child{{color:inherit;opacity:0.8;text-align:right;white-space:nowrap;}}
  .co-right table td:last-child{{font-weight:700;text-align:left;}}
  .status-chip{{display:inline-block;margin-top:6px;padding:3px 10px;
    border:1.5px solid currentColor;font-size:11px;font-weight:800;letter-spacing:1px;
    text-transform:uppercase;border-radius:3px;}}
  /* section heading rows */
  .sec-head{{font-size:11px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;
    background:var(--invoice-accent);padding:4px 8px;color:var(--invoice-accent-text);border-bottom:1px solid var(--invoice-light-border);}}
  /* bordered grid tables */
  .grid-tbl{{width:100%;border-collapse:collapse;margin-bottom:8px;}}
  .grid-tbl th,.grid-tbl td{{border:1px solid #ccc;padding:6px 8px;font-size:13px;}}
  .grid-tbl thead th{{background:var(--invoice-accent);font-weight:800;text-align:center;font-size:12px;
    text-transform:uppercase;letter-spacing:.5px;color:var(--invoice-accent-text);}}
  /* items table */
  .items-tbl{{width:100%;border-collapse:collapse;margin-bottom:8px;}}
  .items-tbl th{{background:var(--invoice-accent);color:var(--invoice-accent-text);padding:8px 8px;font-size:12px;
    letter-spacing:.6px;text-transform:uppercase;font-weight:700;border:1px solid var(--invoice-accent);}}
  .items-tbl td{{border:1px solid #dde1e7;padding:8px 8px;vertical-align:top;font-size:13px;}}
  .items-tbl tbody tr:nth-child(even){{background:#ffffff;}}
  /* summary */
  .summary-tbl{{width:100%;border-collapse:collapse;}}
  .summary-tbl td{{border:1px solid #dde1e7;padding:6px 10px;font-size:13px;}}
  .summary-tbl td:last-child{{text-align:right;font-weight:600;}}
  .summary-tbl .grand-row td{{background:var(--invoice-accent);color:var(--invoice-accent-text);font-weight:800;font-size:14.5px;border-color:var(--invoice-accent);}}
  /* words strip */
  .words-strip{{border:1px solid #dde1e7;padding:8px 12px;font-size:13px;
    margin-bottom:8px;background:#ffffff;}}
  /* footer */
  .inv-footer{{border-top:1.5px solid #222;margin-top:8px;padding-top:8px;
    display:flex;justify-content:space-between;align-items:flex-end;}}
  .sign-block{{text-align:center;}}
  .sign-line{{width:160px;border-top:1.5px solid #111;margin-bottom:4px;margin-top:24px;}}
  .sign-lbl{{font-size:10px;color:#555;}}
  .powered{{font-size:9.5px;color:#94a3b8;margin-top:6px;text-align:right;}}
</style>
</head>
<body>
<div class="wrapper">

  <!-- Print bar -->
  <div class="print-bar no-print">
    <button class="btn-print" onclick="window.print()">🖨&nbsp; Print / Save PDF</button>
    <button class="btn-close" onclick="window.close()">✕ Close</button>
  </div>

  <div class="inv-page">

    <!-- ── COMPANY HEADER ── -->
    <div class="co-header" style="background:{header_bg};color:{header_text};">
      <div class="co-left">
        <img src="{logo_src}" alt="AI SETU Logo" onerror="this.style.display='none'" style="height:44px;object-fit:contain;margin-bottom:4px;display:block;">
        <div class="co-name">{company_name}</div>
        {'<div class="co-sub" style="color:' + header_sub_text + ';">' + company_address + '</div>' if company_address else ''}
        {'<div class="co-sub" style="color:' + header_sub_text + ';">Phone: ' + company_phone + ' | Email: ' + company_email + '</div>' if (company_phone or company_email) else ''}
        {f'<div class="co-sub" style="color:{header_sub_text};">' + company_ids_str + '</div>' if company_ids_str else ''}
      </div>
      <div class="co-right">
        <div class="ti-label">Tax Invoice</div>
        <table style="margin-left:auto;margin-top:6px;color:{header_text};">
          <tr><td>Invoice No:</td><td>{bill.invoice_number}</td></tr>
          <tr><td>Date:</td><td>{invoice_date}</td></tr>
        </table>
        <div class="status-chip">{status_label}</div>
      </div>
    </div>

    <!-- ── BILL DETAILS ── -->
    <div class="sec-head">Bill Details</div>
    <table class="grid-tbl" style="margin-bottom:10px;">
      <thead>
        <tr>
          <th>Reverse Charge</th>
          <th>State</th>
          <th>Code</th>
          <th>Place of Supply</th>
          <th>Payment Type</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td style="text-align:center;">No</td>
          <td style="text-align:center;">Gujarat</td>
          <td style="text-align:center;">24</td>
          <td style="text-align:center;">NA</td>
          <td style="text-align:center;">{payment_type_label}</td>
        </tr>
      </tbody>
    </table>

    <!-- ── BILL TO PARTY ── -->
    <div class="sec-head">Bill To Party</div>
    <table class="grid-tbl" style="margin-bottom:10px;">
      <thead>
        <tr>
          <th style="width:55%;">Customer Details</th>
          <th style="width:22%;">GSTIN</th>
          <th style="width:23%;">PAN</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>
            <strong style="font-size:14px;">{client_name}</strong>
            {'<br><em>' + client_org + '</em>' if client_org else ''}
            {'<br><span style="color:#444;">Email: ' + client_email + '</span>' if client_email else ''}
            {'<br>Phone: ' + client_phone if client_phone and client_phone != '—' else ''}
            {'<br>' + client_address if client_address else ''}
          </td>
          <td style="text-align:center;color:#555;">N.A</td>
          <td style="text-align:center;color:#555;">N.A</td>
        </tr>
      </tbody>
    </table>

    <!-- ── PRODUCT / SERVICE ── -->
    <div class="sec-head">Product / Service</div>
    <table class="items-tbl" style="margin-bottom:10px;">
      <thead>
        <tr>
          <th style="width:36px;text-align:center;">S.No</th>
          <th>Description</th>
          <th style="width:60px;text-align:center;">SAC</th>
          <th style="width:40px;text-align:center;">Qty</th>
          <th style="width:100px;text-align:right;">Rate</th>
          <th style="width:100px;text-align:right;">Amount</th>
          {tax_cols_th}
        </tr>
      </thead>
      <tbody>
        <tr>
          <td style="text-align:center;">1</td>
          <td style="font-weight:600;">{service_desc}</td>
          <td style="text-align:center;">9992</td>
          <td style="text-align:center;">1</td>
          <td style="text-align:right;">₹{item_rate:,.2f}</td>
          <td style="text-align:right;">₹{item_rate:,.2f}</td>
          {tax_cols_td}
        </tr>
      </tbody>
    </table>

    <!-- ── SUMMARY ── -->
    <div class="sec-head">Summary</div>
    <div style="display:flex;gap:16px;margin-bottom:10px;">
      <table class="summary-tbl" style="flex:1;">
        {summary_html}
      </table>
    </div>

    <!-- ── AMOUNT IN WORDS ── -->
    <div class="words-strip">
      <strong>IN WORDS:</strong> {amount_words}
    </div>


    <!-- ── TERMS ── -->
    <div class="sec-head" style="margin-top:10px;">Terms &amp; Conditions</div>
    <div style="padding:10px 14px;font-size:12px;color:#555;border:1px solid #dde1e7;border-top:none;line-height:1.5;">
      {terms_html}
    </div>

    <!-- ── FOOTER ── -->
    <div class="inv-footer">
      <div class="sign-block">
        <div class="sign-line"></div>
        <div class="sign-lbl">Received By, Signed &amp; Stamped</div>
      </div>
      <div class="sign-block">
        <div class="sign-line"></div>
        <div class="sign-lbl">For {company_name}<br>Authorised Signatory</div>
      </div>
    </div>
    <div class="powered">This is a computer generated invoice. For support, contact {company_phone or company_address or company_name}.</div>

  </div><!-- /inv-page -->
</div><!-- /wrapper -->
</body>
</html>"""





