# backend/app/modules/billing/router.py
from typing import List, Any
import hmac as _hmac
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.billing.schemas import (
  BillCreate,
  BillRead,
  BillingWorkflowResolveRequest,
  BillingWorkflowResolveResponse,
  BillingInvoiceActionResponse,
)
from app.modules.billing.service import BillingService
from app.modules.billing.models import Bill  # used by PhonePe callback (see below)

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


@router.post("/workflow/resolve", response_model=BillingWorkflowResolveResponse)
def resolve_invoice_workflow(
  payload: BillingWorkflowResolveRequest,
  db: Session = Depends(get_db),
  current_user: User = Depends(staff_access),
) -> Any:
  """Resolve amount, QR requirement and payable metadata for selected payment/GST type."""
  return BillingService(db).resolve_workflow(payload)

@router.post("/", response_model=BillRead, status_code=status.HTTP_201_CREATED)
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
  status_filter: str | None = None,
  payment_type: str | None = None,
  gst_type: str | None = None,
  search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
) -> Any:
  """List invoices with server-side filters and role-based data scope."""
  return BillingService(db).get_all_bills(
    current_user,
    skip=skip,
    limit=limit,
    status_filter=status_filter,
    payment_type=payment_type,
    gst_type=gst_type,
    search=search,
  )


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
    base_url = str(request.base_url)
    result = await BillingService(db).send_whatsapp_invoice(bill_id, current_user, base_url)
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


# ──────────────────── PhonePe Callback (currently disabled) ─────────────────
#
# ENABLE THIS when you activate PhonePe in service.py:
#   Remove the leading '# ' from each line in the block below.
#
# @router.post("/phonepe-callback")
# async def phonepe_payment_callback(
#     request: Request,
#     db: Session = Depends(get_db),
# ):
#     """
#     PhonePe posts here after payment succeeds/fails.
#     Verifies the X-VERIFY checksum before trusting the payload.
#     Marks invoice as PAID if payment is successful.
#     """
#     import hashlib, base64, json as _json
#     from app.core.config import settings
#     body = await request.body()
#     data = await request.json()
#
#     # Verify checksum
#     response_b64  = data.get("response", "")
#     x_verify      = request.headers.get("X-VERIFY", "")
#     expected_hash = hashlib.sha256((response_b64 + settings.PHONEPE_SALT_KEY).encode()).hexdigest()
#     expected_chk  = expected_hash + "###" + settings.PHONEPE_SALT_INDEX
#     if not _hmac.compare_digest(x_verify, expected_chk):
#         raise HTTPException(status_code=400, detail="Invalid PhonePe checksum")
#
#     # Decode response
#     decoded  = _json.loads(base64.b64decode(response_b64).decode())
#     txn_id   = decoded.get("data", {}).get("merchantTransactionId", "")
#     state    = decoded.get("data", {}).get("state", "")   # "COMPLETED" | "FAILED"
#
#     # Extract invoice number from txn_id (format: MT-PInv/2026/001-xxxxx)
#     if state == "COMPLETED" and txn_id:
#         inv_no_part = txn_id.replace("MT-", "").rsplit("-", 1)[0].replace("-", "/")
#         bill = db.query(Bill).filter(Bill.invoice_number == inv_no_part).first()
#         if bill:
#             bill.invoice_status = "PAID"
#             bill.status         = "PAID"
#             db.commit()
#
#     return {"success": True}


# ──────────────────── Public Invoice View (no auth, HMAC token) ───────────────

@router.get("/{bill_id}/invoice-public", response_class=HTMLResponse)
def get_invoice_public(
    bill_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    """Return the invoice HTML for clients via a secure HMAC-signed link (no login required)."""
    expected = BillingService._invoice_public_token(bill_id)
    if not _hmac.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Invalid or expired invoice link")
    svc = BillingService(db)
    bill = svc.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Invoice not found")
    iv_settings = svc.get_invoice_defaults()
    html = _build_invoice_html(bill, iv_settings)
    return HTMLResponse(content=html)


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

    company_name    = settings.get("company_name")    or "CRM AI SETU"
    company_address = settings.get("company_address") or ""
    company_phone   = settings.get("company_phone")   or ""
    company_email   = settings.get("company_email")   or ""
    company_gstin   = settings.get("company_gstin")   or ""
    company_pan     = settings.get("company_pan")     or ""
    company_cin     = settings.get("company_cin")     or ""
    company_cst     = settings.get("company_cst_code") or ""
    upi_id          = settings.get("payment_upi_id")  or ""
    upi_name        = settings.get("payment_account_name") or company_name
    qr_img_url      = settings.get("payment_qr_image_url") or ""
    bank_name       = settings.get("payment_bank_name") or ""
    bank_account_no = settings.get("payment_account_number") or ""
    bank_ifsc       = settings.get("payment_ifsc") or ""
    bank_branch     = settings.get("payment_branch") or ""

    header_bg = settings.get("invoice_header_bg") or "#1f2937"

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

    payment_type_label = {
      "BUSINESS_ACCOUNT": "Business Account",
      "PERSONAL_ACCOUNT": "Personal Account",
      "CASH": "Cash",
    }.get(bill.payment_type, bill.payment_type or "-")
    gst_type_label = "With GST" if is_with_gst else "Without GST"

    status_label = {
        "DRAFT":                "Draft",
        "PENDING_VERIFICATION": "Pending",
        "VERIFIED":             "Verified",
        "SENT":                 "Paid",
    }.get(bill.invoice_status, bill.invoice_status)

    # ── Safe title / default PDF filename ───────────────────────────────────
    _safe = lambda s: s.replace('"','').replace('<','').replace('>','').replace('/','').replace('\\','').strip()
    pdf_title = f"Invoice-{bill.invoice_number} - {_safe(client_name)}"

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

    # ── Bank / QR section ────────────────────────────────────────────────────
    payment_section = ""
    if bill.payment_type == "CASH":
      payment_section = ""
    elif qr_img_url:
        payment_section = f"""
        <div class="bank-box">
          <div class="sec-head">Scan to Pay</div>
          <img src="{qr_img_url}" alt="Payment QR" style="width:110px;height:110px;object-fit:contain;margin:6px 0;" />
          <table style="width:100%;font-size:12px;margin-top:6px;">
            <tr><td class="lbl">UPI ID</td><td style="font-weight:700;">{upi_id or '-'}</td></tr>
            <tr><td class="lbl">Account Name</td><td style="font-weight:700;">{upi_name or '-'}</td></tr>
            {('<tr><td class="lbl">Bank</td><td style="font-weight:700;">' + bank_name + '</td></tr>') if bank_name else ''}
            {('<tr><td class="lbl">A/C No</td><td style="font-weight:700;">' + bank_account_no + '</td></tr>') if bank_account_no else ''}
            {('<tr><td class="lbl">IFSC</td><td style="font-weight:700;">' + bank_ifsc + '</td></tr>') if bank_ifsc else ''}
            {('<tr><td class="lbl">Branch</td><td style="font-weight:700;">' + bank_branch + '</td></tr>') if bank_branch else ''}
          </table>
        </div>"""
    elif upi_id:
        payment_section = f"""
        <div class="bank-box">
          <div class="sec-head">Payment Details</div>
          <table style="width:100%;font-size:12px;margin-top:6px;">
            <tr><td style="color:#666;padding:2px 0;">UPI ID</td><td style="font-weight:700;padding:2px 6px;">{upi_id}</td></tr>
            <tr><td style="color:#666;padding:2px 0;">Account Name</td><td style="font-weight:700;padding:2px 6px;">{upi_name}</td></tr>
            {('<tr><td style="color:#666;padding:2px 0;">Bank</td><td style="font-weight:700;padding:2px 6px;">' + bank_name + '</td></tr>') if bank_name else ''}
            {('<tr><td style="color:#666;padding:2px 0;">A/C No</td><td style="font-weight:700;padding:2px 6px;">' + bank_account_no + '</td></tr>') if bank_account_no else ''}
            {('<tr><td style="color:#666;padding:2px 0;">IFSC</td><td style="font-weight:700;padding:2px 6px;">' + bank_ifsc + '</td></tr>') if bank_ifsc else ''}
            {('<tr><td style="color:#666;padding:2px 0;">Branch</td><td style="font-weight:700;padding:2px 6px;">' + bank_branch + '</td></tr>') if bank_branch else ''}
          </table>
        </div>"""

    # Conditional rendering helpers
    def opt_row(label, val):
        return f'<tr><td class="lbl">{label}</td><td>{val}</td></tr>' if val else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{pdf_title}</title>
<style>
  /* Force all background colours and images to print ─────────────────────── */
  *{{margin:0;padding:0;box-sizing:border-box;
     -webkit-print-color-adjust:exact!important;
     print-color-adjust:exact!important;}}
  @page{{size:A4 portrait;margin:0;}}
  html{{background:#e2e8f0;}}
  body{{font-family:Arial,Helvetica,sans-serif;background:#e2e8f0;font-size:13px;color:#111;}}
  .wrapper{{width:210mm;min-height:297mm;margin:18px auto;background:#fff;
    box-shadow:0 4px 32px rgba(0,0,0,0.15);}}
  /* ── print bar ── */
  .print-bar{{background:#0f172a;padding:12px 20px;display:flex;gap:12px;align-items:center;}}
  .print-bar button{{border:none;padding:9px 26px;font-size:13px;font-weight:700;border-radius:7px;cursor:pointer;transition:opacity .15s;}}
  .print-bar button:hover{{opacity:.85;}}
  .btn-print{{background:#6366f1;color:#fff;}}
  .btn-close{{background:#334155;color:#e2e8f0;}}
  @media print{{
    .print-bar{{display:none!important;}}
    html,body{{background:#fff!important;margin:0!important;padding:0!important;}}
    .wrapper{{width:210mm!important;min-height:297mm!important;margin:0!important;box-shadow:none!important;}}
    .inv-page{{padding:10mm 12mm 8mm 12mm!important;}}
  }}
  /* ── invoice page ── */
  .inv-page{{padding:12mm 14mm 10mm 14mm;}}
  /* company header */
  .co-header{{display:flex;justify-content:space-between;align-items:flex-start;
    border:1px solid #d1d5db;padding:12px 14px;margin-bottom:12px;}}
  .co-left .co-name{{font-size:18px;font-weight:900;letter-spacing:.2px;}}
  .co-left .co-sub{{font-size:11px;margin-top:4px;max-width:420px;line-height:1.55;}}
  .co-right{{text-align:right;}}
  .co-right .ti-label{{font-size:17px;font-weight:900;letter-spacing:.6px;}}
  .co-right table td{{font-size:12px;padding:2px 5px;}}
  .co-right table td:first-child{{opacity:.75;text-align:right;white-space:nowrap;}}
  .co-right table td:last-child{{font-weight:700;text-align:left;}}
  .status-chip{{display:inline-block;margin-top:6px;padding:3px 14px;
    border:1.5px solid rgba(255,255,255,0.55);font-size:10.5px;font-weight:800;letter-spacing:1px;
    text-transform:uppercase;border-radius:3px;}}
  /* section heading rows */
  .sec-head{{font-size:10.5px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;
    background:#f1f5f9!important;padding:6px 10px;color:#374151;border-bottom:1px solid #dde1e7;}}
  /* bordered grid tables */
  .grid-tbl{{width:100%;border-collapse:collapse;margin-bottom:12px;}}
  .grid-tbl th,.grid-tbl td{{border:1px solid #ccc;padding:6px 10px;font-size:12px;}}
  .grid-tbl thead th{{background:#f8fafc!important;font-weight:800;text-align:center;font-size:11px;
    text-transform:uppercase;letter-spacing:.5px;color:#374151;}}
  /* items table */
  .items-tbl{{width:100%;border-collapse:collapse;margin-bottom:10px;}}
  .items-tbl th{{background:#1e293b!important;color:#fff!important;padding:8px 9px;font-size:11px;
    letter-spacing:.6px;text-transform:uppercase;font-weight:700;border:1px solid #1e293b;}}
  .items-tbl td{{border:1px solid #dde1e7;padding:9px;vertical-align:top;font-size:12.5px;}}
  .items-tbl tbody tr:nth-child(even){{background:#f8fafc!important;}}
  /* summary */
  .summary-tbl{{width:100%;border-collapse:collapse;}}
  .summary-tbl td{{border:1px solid #dde1e7;padding:6px 12px;font-size:12.5px;}}
  .summary-tbl td:last-child{{text-align:right;font-weight:600;}}
  .summary-tbl .grand-row td{{background:#1e293b!important;color:#fff!important;font-weight:800;font-size:14px;border-color:#1e293b;}}
  /* words strip */
  .words-strip{{border:1px solid #dde1e7;padding:9px 14px;font-size:12px;
    margin-bottom:12px;background:#fffbeb!important;}}
  /* bank box */
  .bank-box{{border:1px solid #dde1e7;border-radius:6px;padding:12px 14px;
    font-size:12px;margin-top:10px;}}
  .bank-box table td{{padding:3px 8px;font-size:12px;}}
  .bank-box .lbl{{color:#666;white-space:nowrap;}}
  /* footer */
  .inv-footer{{border-top:1.5px solid #222;margin-top:12px;padding-top:12px;
    display:flex;justify-content:space-between;align-items:flex-end;}}
  .sign-block{{text-align:center;}}
  .sign-line{{width:160px;border-top:1.5px solid #111;margin-bottom:4px;margin-top:36px;}}
  .sign-lbl{{font-size:11px;color:#555;}}
  .powered{{font-size:10px;color:#94a3b8;margin-top:8px;text-align:right;}}
</style>
</head>
<body>
<div class="wrapper">

  <!-- Print bar -->
  <div class="print-bar no-print">
    <button class="btn-print" onclick="window.print()">🖨&nbsp; Print / Save PDF</button>
    <button class="btn-close" onclick="window.close()">✕ Close</button>
    <span style="color:#94a3b8;font-size:12px;margin-left:8px;">Default filename: <em style="color:#e2e8f0;">{pdf_title}</em></span>
  </div>

  <div class="inv-page">

    <!-- ── COMPANY HEADER ── -->
    <div class="co-header" style="background:{header_bg};color:{header_text};">
      <div class="co-left">
        <img src="{logo_src}" alt="AI SETU Logo" onerror="this.style.display='none'" style="height:44px;object-fit:contain;margin-bottom:4px;display:block;">
        <div class="co-name">{company_name}</div>
        {'<div class="co-sub" style="color:' + header_sub_text + ';">' + company_address + '</div>' if company_address else ''}
        {'<div class="co-sub" style="color:' + header_sub_text + ';">Phone: ' + company_phone + ' | Email: ' + company_email + '</div>' if (company_phone or company_email) else ''}
        <div class="co-sub" style="color:{header_sub_text};">GSTIN: {company_gstin or '-'} | PAN: {company_pan or '-'} | CIN: {company_cin or '-'} | CST Code: {company_cst or '-'}</div>
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
        </tr>
      </thead>
      <tbody>
        <tr>
          <td style="text-align:center;">No</td>
          <td style="text-align:center;">Gujarat</td>
          <td style="text-align:center;">24</td>
          <td style="text-align:center;">NA</td>
        </tr>
      </tbody>
    </table>

    <table class="grid-tbl" style="margin-bottom:10px;">
      <thead>
        <tr>
          <th>Payment Type</th>
          <th>GST Type</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td style="text-align:center;">{payment_type_label}</td>
          <td style="text-align:center;">{gst_type_label}</td>
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
            <strong style="font-size:13px;">{client_name}</strong>
            {'<br><span style="color:#444;">' + client_email + '</span>' if client_email else ''}
            {'<br>' + client_phone if client_phone and client_phone != '—' else ''}
            {'<br><em>' + client_org + '</em>' if client_org else ''}
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
          <th style="width:90px;text-align:right;">Rate</th>
          <th style="width:90px;text-align:right;">Amount</th>
          <th style="width:80px;text-align:right;">Discount</th>
          <th style="width:90px;text-align:right;">Taxable</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td style="text-align:center;">1</td>
          <td style="font-weight:600;">{service_desc}</td>
          <td style="text-align:center;">9992</td>
          <td style="text-align:center;">1</td>
          <td style="text-align:right;">₹{subtotal:,.2f}</td>
          <td style="text-align:right;">₹{subtotal:,.2f}</td>
          <td style="text-align:right;">-</td>
          <td style="text-align:right;font-weight:700;">₹{subtotal:,.2f}</td>
        </tr>
      </tbody>
    </table>

    <!-- ── SUMMARY ── -->
    <div class="sec-head">Summary</div>
    <div style="display:flex;gap:16px;margin-bottom:10px;">
      <table class="summary-tbl" style="flex:1;">
        <tr><td>Total Before Tax</td><td>₹{subtotal:,.2f}</td></tr>
        {'<tr><td>CGST (' + str(cgst_rate) + '%)</td><td>₹' + f"{cgst_amt:,.2f}" + '</td></tr>' if cgst_rate > 0 else '<tr><td>CGST (0%)</td><td>₹0.00</td></tr>'}
        {'<tr><td>SGST (' + str(sgst_rate) + '%)</td><td>₹' + f"{sgst_amt:,.2f}" + '</td></tr>' if sgst_rate > 0 else '<tr><td>SGST (0%)</td><td>₹0.00</td></tr>'}
        <tr><td>Total Tax</td><td>₹{total_tax:,.2f}</td></tr>
        <tr><td>Round Off</td><td>₹{round_off:,.2f}</td></tr>
        <tr class="grand-row"><td>Total After Tax</td><td>₹{rounded_total:,.2f}</td></tr>
      </table>
    </div>

    <!-- ── AMOUNT IN WORDS ── -->
    <div class="words-strip">
      <strong>IN WORDS:</strong> {amount_words}
    </div>

    <!-- ── BANK DETAILS ── -->
    {'<div class="sec-head">Bank Details</div>' + payment_section if payment_section else ''}

    <!-- ── TERMS ── -->
    <div class="sec-head" style="margin-top:10px;">Terms &amp; Conditions</div>
    <div style="padding:8px 12px;font-size:11px;color:#555;border:1px solid #dde1e7;border-top:none;">
      &bull; Subject to Surat Jurisdiction
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

