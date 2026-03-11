from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.billing.schemas import BillCreate, BillRead
from app.modules.billing.service import BillingService

router = APIRouter()

# Staff who can create / view invoices
staff_access = RoleChecker([
    UserRole.ADMIN,
    UserRole.SALES,
    UserRole.TELESALES,
    UserRole.PROJECT_MANAGER,
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
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access),
) -> Any:
    """List invoices filtered by the calling user's role."""
    return BillingService(db).get_all_bills(current_user, skip=skip, limit=limit)


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


# ──────────────────── Workflow ─────────────────────────────────────────────────

@router.patch("/{bill_id}/verify", response_model=BillRead)
def verify_invoice(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
) -> Any:
    """Admin verifies the invoice (PENDING_VERIFICATION → VERIFIED)."""
    return BillingService(db).verify_invoice(bill_id, current_user)


@router.post("/{bill_id}/send-whatsapp")
async def send_invoice_whatsapp(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
) -> Any:
    """
    Admin sends verified invoice to client via WhatsApp.
    Auto-creates client if not already in the system.
    Returns the WhatsApp URL to open.
    """
    result = await BillingService(db).send_whatsapp_invoice(bill_id, current_user)
    bill = result["bill"]
    wa_url = result["wa_url"]
    return {
        "success": True,
        "wa_url": wa_url,
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
    import math
    from datetime import datetime, timezone

    company_name    = settings.get("company_name")    or "CRM AI SETU"
    company_address = settings.get("company_address") or ""
    company_phone   = settings.get("company_phone")   or ""
    company_gstin   = settings.get("company_gstin")   or ""
    upi_id          = settings.get("payment_upi_id")  or ""
    upi_name        = settings.get("payment_account_name") or company_name
    qr_img_url      = settings.get("payment_qr_image_url") or ""

    _dt = bill.created_at if bill.created_at else datetime.now(timezone.utc)
    invoice_date = _dt.strftime("%d %b %Y, %I:%M %p").lstrip("0")

    client_name    = bill.invoice_client_name    or "—"
    client_phone   = bill.invoice_client_phone   or "—"
    client_email   = bill.invoice_client_email   or ""
    client_address = bill.invoice_client_address or ""
    client_org     = bill.invoice_client_org     or ""

    service_desc   = bill.service_description or "CRM AI SETU Software – Annual Subscription"
    amount         = bill.amount or 0.0

    # Tax computation (0% GST by default — edit if needed)
    subtotal       = amount
    cgst_rate      = 0       # set to 9 to enable 9% CGST
    sgst_rate      = 0       # set to 9 to enable 9% SGST
    cgst_amt       = round(subtotal * cgst_rate / 100, 2)
    sgst_amt       = round(subtotal * sgst_rate / 100, 2)
    total_tax      = cgst_amt + sgst_amt
    total_before_round = subtotal + total_tax
    rounded_total  = round(total_before_round)
    round_off      = round(rounded_total - total_before_round, 2)

    status_label = {
        "DRAFT":                "Draft",
        "PENDING_VERIFICATION": "Pending",
        "VERIFIED":             "Verified",
        "SENT":                 "Paid",
    }.get(bill.invoice_status, bill.invoice_status)

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
    if qr_img_url:
        payment_section = f"""
        <div class="bank-box">
          <div class="sec-head">Scan to Pay</div>
          <img src="{qr_img_url}" alt="Payment QR" style="width:110px;height:110px;object-fit:contain;margin:6px 0;" />
          <div style="font-size:12px;font-weight:700;">{upi_id}</div>
          <div style="font-size:11px;color:#555;">{upi_name}</div>
        </div>"""
    elif upi_id:
        payment_section = f"""
        <div class="bank-box">
          <div class="sec-head">Payment Details</div>
          <table style="width:100%;font-size:12px;margin-top:6px;">
            <tr><td style="color:#666;padding:2px 0;">UPI ID</td><td style="font-weight:700;padding:2px 6px;">{upi_id}</td></tr>
            <tr><td style="color:#666;padding:2px 0;">Account Name</td><td style="font-weight:700;padding:2px 6px;">{upi_name}</td></tr>
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
<title>Tax Invoice — {bill.invoice_number}</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box;}}
  @page{{size:A4;margin:0;}}
  body{{font-family:Arial,Helvetica,sans-serif;background:#f4f6f9;font-size:12.5px;color:#111;}}
  .wrapper{{width:210mm;min-height:297mm;margin:0 auto;background:#fff;}}
  /* ── print bar ── */
  .print-bar{{background:#1e293b;padding:10px 18px;display:flex;gap:10px;align-items:center;}}
  .print-bar button{{border:none;padding:8px 22px;font-size:13px;font-weight:700;border-radius:6px;cursor:pointer;}}
  .btn-print{{background:#6366f1;color:#fff;}}
  .btn-close{{background:#334155;color:#e2e8f0;}}
  @media print{{.print-bar{{display:none!important;}}body{{background:#fff;}}}}
  /* ── invoice page ── */
  .inv-page{{padding:14mm 14mm 10mm 14mm;}}
  /* company header */
  .co-header{{display:flex;justify-content:space-between;align-items:flex-start;
    border-bottom:2px solid #222;padding-bottom:10px;margin-bottom:10px;}}
  .co-left .co-name{{font-size:17px;font-weight:900;letter-spacing:.2px;}}
  .co-left .co-sub{{font-size:10.5px;color:#444;margin-top:3px;max-width:320px;line-height:1.5;}}
  .co-right{{text-align:right;}}
  .co-right .ti-label{{font-size:18px;font-weight:900;letter-spacing:1px;color:#111;}}
  .co-right table td{{font-size:11px;padding:1px 4px;}}
  .co-right table td:first-child{{color:#666;text-align:right;white-space:nowrap;}}
  .co-right table td:last-child{{font-weight:700;text-align:left;}}
  .status-chip{{display:inline-block;margin-top:6px;padding:3px 12px;
    border:1.5px solid #222;font-size:10px;font-weight:800;letter-spacing:1px;
    text-transform:uppercase;border-radius:3px;}}
  /* section heading rows */
  .sec-head{{font-size:10px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;
    background:#f1f5f9;padding:5px 8px;color:#374151;border-bottom:1px solid #dde1e7;}}
  /* bordered grid tables */
  .grid-tbl{{width:100%;border-collapse:collapse;margin-bottom:10px;}}
  .grid-tbl th,.grid-tbl td{{border:1px solid #ccc;padding:5px 8px;font-size:11.5px;}}
  .grid-tbl thead th{{background:#f8fafc;font-weight:800;text-align:center;font-size:10.5px;
    text-transform:uppercase;letter-spacing:.5px;color:#374151;}}
  /* items table */
  .items-tbl{{width:100%;border-collapse:collapse;margin-bottom:8px;}}
  .items-tbl th{{background:#1e293b;color:#fff;padding:7px 8px;font-size:10.5px;
    letter-spacing:.6px;text-transform:uppercase;font-weight:700;border:1px solid #1e293b;}}
  .items-tbl td{{border:1px solid #dde1e7;padding:8px 8px;vertical-align:top;}}
  .items-tbl tbody tr:nth-child(even){{background:#fafbfc;}}
  /* summary */
  .summary-tbl{{width:100%;border-collapse:collapse;}}
  .summary-tbl td{{border:1px solid #dde1e7;padding:5px 10px;font-size:12px;}}
  .summary-tbl td:last-child{{text-align:right;font-weight:600;}}
  .summary-tbl .grand-row td{{background:#1e293b;color:#fff;font-weight:800;font-size:13.5px;border-color:#1e293b;}}
  /* words strip */
  .words-strip{{border:1px solid #dde1e7;padding:8px 12px;font-size:11.5px;
    margin-bottom:10px;background:#fffbeb;}}
  /* bank box */
  .bank-box{{border:1px solid #dde1e7;border-radius:6px;padding:10px 14px;
    font-size:11.5px;margin-top:8px;}}
  .bank-box table td{{padding:2px 6px;font-size:11.5px;}}
  .bank-box .lbl{{color:#666;white-space:nowrap;}}
  /* footer */
  .inv-footer{{border-top:1.5px solid #222;margin-top:10px;padding-top:10px;
    display:flex;justify-content:space-between;align-items:flex-end;}}
  .sign-block{{text-align:center;}}
  .sign-line{{width:160px;border-top:1.5px solid #111;margin-bottom:4px;margin-top:32px;}}
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
    <div class="co-header">
      <div class="co-left">
        <img src="/frontend/images/logo.png" alt="" onerror="this.style.display='none'" style="height:44px;object-fit:contain;margin-bottom:4px;display:block;">
        <div class="co-name">{company_name}</div>
        {'<div class="co-sub">' + company_address + '</div>' if company_address else ''}
        {'<div class="co-sub">Phone: ' + company_phone + '</div>' if company_phone else ''}
        {'<div class="co-sub">GSTIN: ' + company_gstin + ' | PAN: N/A</div>' if company_gstin else ''}
      </div>
      <div class="co-right">
        <div class="ti-label">Tax Invoice</div>
        <table style="margin-left:auto;margin-top:6px;">
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

