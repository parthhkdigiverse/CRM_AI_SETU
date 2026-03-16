---
description: Testing WhatsApp API and PhonePe Payment Gateway Setup
---
// turbo-all
# Workflow: Testing WhatsApp & PhonePe Integration

Follow these steps to verify the invoice payment and dispatch system.

## 1. Environment Verification
- Check [backend/.env](file:///e:/CRM%20AI%20SETU/backend/.env) for valid `PHONEPE_MERCHANT_ID`, `PHONEPE_SALT_KEY`, and `WHATSAPP_TOKEN`.
- Ensure the backend server is running: `python app.py`.

## 2. Invoicing Workflow Test
1.  Open the [Billing Page](http://127.0.0.1:8000/frontend/template/billing.html).
2.  Click **New Invoice**.
3.  **Step 1**: Fill in client details. Note that the **Amount** is read-only and managed by Admin settings.
4.  **Step 2**: Click **Proceed**. A QR code should appear. This is the PhonePe/UPI intent for the customer.
5.  **Step 3**: Click **Confirm & Generate**.
    - This creates the invoice in the system.
    - Automates verification.
    - Attempts to send via WhatsApp.

## 3. Resolving WhatsApp 502 Errors
If WhatsApp sending fails with a `502 Bad Gateway`:
- Check terminal logs for `Meta: Authentication Error (code=190)`.
- This means your `WHATSAPP_TOKEN` is expired.
- Refresh the token in Meta Business Suite and update `.env`.

## 4. Admin Settings Test
- Click the **Gear Icon** (Admin/PM only).
- Update the **Default Amount**.
- Open the **New Invoice** modal and verify the amount has updated to your new default.
