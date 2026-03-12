import json
import urllib.request
import urllib.error
from urllib.parse import urlencode

BASE = "http://127.0.0.1:8000/api"


def req(method: str, path: str, data=None, token: str | None = None, form=False):
    url = BASE + path
    headers = {}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        if form:
            body = urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url=url, method=method, data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            ctype = resp.headers.get("Content-Type", "")
            parsed = None
            if raw and "application/json" in ctype:
                parsed = json.loads(raw)
            return resp.getcode(), raw, parsed
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        try:
            parsed = json.loads(raw) if raw else None
        except Exception:
            parsed = None
        return e.code, raw, parsed


def line(msg: str):
    print(msg, flush=True)


def main():
    line("=== Login ===")
    code, _, login = req("POST", "/auth/login", {"username": "admin@example.com", "password": "password123"}, form=True)
    if code != 200 or not login or not login.get("access_token"):
        line(f"LOGIN_FAIL status={code} body={login}")
        return
    token = login["access_token"]
    line("TOKEN_OK")

    line("=== Save settings ===")
    settings = {
        "invoice_default_amount": 12000,
        "personal_without_gst_default_amount": 12000,
        "payment_upi_id": "aisetu@upi",
        "payment_account_name": "AI SETU",
        "payment_qr_image_url": "https://example.com/qr.png",
        "invoice_seq_with_gst": 1,
        "invoice_seq_without_gst": 1,
        "invoice_verifier_roles": "ADMIN",
        "invoice_header_bg": "#1f2937",
    }
    code, _, st = req("PUT", "/billing/settings", settings, token=token)
    line(f"SETTINGS status={code} seq_with_gst={st.get('invoice_seq_with_gst') if st else None} seq_without_gst={st.get('invoice_seq_without_gst') if st else None}")

    line("=== Resolve cases ===")
    cases = [
        {"payment_type": "BUSINESS_ACCOUNT", "gst_type": "WITH_GST", "amount": None},
        {"payment_type": "PERSONAL_ACCOUNT", "gst_type": "WITH_GST", "amount": 15000},
        {"payment_type": "PERSONAL_ACCOUNT", "gst_type": "WITHOUT_GST", "amount": None},
        {"payment_type": "CASH", "gst_type": "WITH_GST", "amount": 18000},
        {"payment_type": "CASH", "gst_type": "WITHOUT_GST", "amount": 5000},
    ]
    for c in cases:
        code, _, r = req("POST", "/billing/workflow/resolve", c, token=token)
        line(f"RESOLVE {c['payment_type']}/{c['gst_type']} status={code} amount={r.get('amount') if r else None} requires_qr={r.get('requires_qr') if r else None}")

    code, _, bad = req("POST", "/billing/workflow/resolve", {"payment_type": "BUSINESS_ACCOUNT", "gst_type": "WITHOUT_GST", "amount": 12000}, token=token)
    line(f"RESOLVE_INVALID status={code} detail={bad.get('detail') if bad else None}")

    line("=== Create sequence invoices ===")
    inv_payloads = [
        {"invoice_client_name": "Client A", "invoice_client_phone": "9000000001", "payment_type": "BUSINESS_ACCOUNT", "gst_type": "WITH_GST", "amount": 6999, "service_description": "LAST PRELIMS"},
        {"invoice_client_name": "Client B", "invoice_client_phone": "9000000002", "payment_type": "CASH", "gst_type": "WITH_GST", "amount": 8000, "service_description": "LAST PRELIMS"},
        {"invoice_client_name": "Client C", "invoice_client_phone": "9000000003", "payment_type": "PERSONAL_ACCOUNT", "gst_type": "WITHOUT_GST", "amount": None, "service_description": "LAST PRELIMS"},
        {"invoice_client_name": "Client D", "invoice_client_phone": "9000000004", "payment_type": "CASH", "gst_type": "WITHOUT_GST", "amount": 5000, "service_description": "LAST PRELIMS"},
    ]
    created = []
    for p in inv_payloads:
        code, raw, r = req("POST", "/billing/", p, token=token)
        if code == 201:
            created.append(r)
            line(f"CREATE_OK id={r.get('id')} inv={r.get('invoice_number')} type={r.get('payment_type')}/{r.get('gst_type')} amount={r.get('amount')}")
        else:
            line(f"CREATE_FAIL status={code} body={raw}")

    line("=== Filters ===")
    code, _, f1 = req("GET", "/billing/?payment_type=CASH&gst_type=WITH_GST&limit=20", token=token)
    code2, _, f2 = req("GET", "/billing/?gst_type=WITHOUT_GST&limit=20", token=token)
    line(f"FILTER_CASH_WITH_GST status={code} count={len(f1) if isinstance(f1, list) else 'NA'}")
    line(f"FILTER_WITHOUT_GST status={code2} count={len(f2) if isinstance(f2, list) else 'NA'}")

    if created:
        first = created[0]
        fid = first["id"]
        line("=== Actions / Verify / Send / Invoice HTML ===")
        code, _, act = req("GET", f"/billing/{fid}/actions", token=token)
        line(f"ACTIONS status={code} can_verify={act.get('can_verify') if act else None} can_send={act.get('can_send_whatsapp') if act else None}")

        code, _, ver = req("PATCH", f"/billing/{fid}/verify", token=token)
        line(f"VERIFY status={code} invoice_status={ver.get('invoice_status') if ver else None}")

        code, _, snd = req("POST", f"/billing/{fid}/send-whatsapp", token=token)
        line(f"SEND status={code} invoice_status={snd.get('invoice_status') if snd else None} wa_url={bool(snd.get('wa_url')) if snd else None} phonepe_link={bool(snd.get('phonepe_payment_link')) if snd else None}")

        code, raw, _ = req("GET", f"/billing/{fid}/invoice-html", token=token)
        line(f"INVOICE_HTML status={code} has_cgst9={'CGST (9%)' in raw if raw else False} has_white_logo={'/frontend/images/white%20logo.png' in raw if raw else False}")

    line("=== DONE ===")


if __name__ == "__main__":
    main()
