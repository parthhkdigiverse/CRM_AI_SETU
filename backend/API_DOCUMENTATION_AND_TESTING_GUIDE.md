# CRM AI SETU - Comprehensive API Documentation & Testing Guide

This document provides a detailed explanation of every API endpoint in the CRM AI SETU backend, its business purpose, the roles authorized to use it, and step-by-step instructions on how to test it using the built-in Swagger UI.

## Setup & Authentication

Before testing any endpoint, you must start the server and authenticate.

1. **Start Server:** Run `uvicorn app.main:app --reload --port 8000` from the `backend` directory.
2. **Access Swagger:** Open `http://127.0.0.1:8000/docs` in your browser.
3. **Authenticate:**
   * Many APIs require authentication. Click the green **Authorize** button at the top right of Swagger.
   * Enter your credentials (e.g., username `admin@example.com`, password `password123` if you've seeded an admin user, or register a new one). This sets the Authorization header for subsequent requests.

---

## 1. Authentication Module (`/api/auth`)

### `POST /api/auth/register`
* **Purpose:** Registers a new user in the system.
* **Roles:** Public (Unauthenticated)
* **How to Test:** Expand the endpoint, click "Try it out", provide the following JSON payload, and execute. Note the returned `id` for employee mapping later.
```json
{
  "email": "admin2@example.com",
  "name": "Test Admin",
  "password": "Security123!",
  "phone": "9876543210",
  "role": "ADMIN",
  "is_active": true
}
```

### `POST /api/auth/login`
* **Purpose:** Authenticates a user and returns JWT tokens (`access_token` and `refresh_token`).
* **Roles:** Public (Unauthenticated)
* **How to Test:** Enter `username` (email) and `password` in the form. The response body contains the tokens. Swagger uses this internally when you use the "Authorize" button.
```json
{
  "username": "admin@example.com",
  "password": "password123"
}
```

### `POST /api/auth/refresh`
* **Purpose:** Exchanges a valid `refresh_token` for a new `access_token` without requiring the user to log in again.
* **Roles:** Public (requires a valid refresh token in the header)
* **How to Test in Swagger:** 
  1. Test `/api/auth/login` and carefully copy the very long `refresh_token` string from the response payload.
  2. Scroll to the very top of the Swagger document and click the green **Authorize** button.
  3. If you are already authorized, click **Logout** inside that popup box to clear your old token.
  4. Paste the `refresh_token` you just copied into the text box, click **Authorize**, and then click **Close**.
  5. Scroll down to `POST /api/auth/refresh`, click "Try it out", and click **Execute** without any JSON body. The server will see your refresh token and return a brand new set of tokens.
  6. **Important:** To test other APIs after this, you must go back to the top, click Authorize -> Logout again, and paste in your fresh `access_token`.

### `POST /api/auth/logout`
* **Purpose:** Logs the user out of the backend CRM system.
* **Roles:** Any authenticated user.
* **How to Test in Swagger:** Ensure you are authorized with an `access_token` via the green Authorize button at the top. Click Execute on this endpoint. It will return a successful `200 OK` message. 
* *(Note: Because we use stateless JWT technology, "true" logout actually happens on your frontend when React deletes your stored token. This API is a handshake to confirm the session end, and is where token-blacklisting would be added in the future).*

---

## 2. Users Module (`/api/users`)

### `PATCH /api/users/{user_id}/role`
* **Purpose:** Changes the role of a specific user.
* **Roles:** Admin only.
* **How to Test:** Provide the `user_id` and the new `role` string (e.g., `PROJECT_MANAGER`).
```json
{
  "role": "PROJECT_MANAGER"
}
```

---

## 3. Employees Module (`/api/employees`)

### `POST /api/employees/`
* **Purpose:** Creates an employee record linking HR details (salary, department, target) to a system User account.
* **Roles:** Admin only.
* **How to Test:** Provide the following JSON payload, ensuring `user_id` matches a registered user.
```json
{
  "employee_code": "EMP-001",
  "joining_date": "2026-03-01",
  "base_salary": 50000.0,
  "target": 10,
  "department": "Sales",
  "user_id": 2
}
```

### `GET /api/employees/`
* **Purpose:** Retrieves a list of all employees.
* **Roles:** Admin, PMs.
* **How to Test:** Execute to view the array of employee records.

### `GET /api/employees/{employee_id}`
* **Purpose:** Retrieves detailed information for a specific employee.
* **Roles:** Admin, PMs.
* **How to Test:** Provide the `employee_id`.

### `PATCH /api/employees/{employee_id}`
* **Purpose:** Updates employee HR details (salary, target, department).
* **Roles:** Admin only.
* **How to Test:** Provide the `employee_id` and the fields you wish to update.
```json
{
  "base_salary": 55000.0,
  "department": "Senior Sales"
}
```

### `GET /api/employees/{employee_id}/id-card`
* **Purpose:** Generates a digital ID card for the employee.
* **Roles:** Admin, or the Employee themselves.
* **How to Test:** Provide the `employee_id`. The system returns formatted ID card data (or triggers a PDF generation if fully implemented).

### `GET /api/employees/{pm_id}/availability`
* **Purpose:** Calculates free 1-hour meeting slots for a Project Manager for a specific date (between 9 AM and 6 PM).
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Provide the `pm_id` in the path, and the mandatory `date` as a query parameter (format: `YYYY-MM-DD`). The response lists available hours avoiding existing non-cancelled meetings.

---

## 4. Areas & Shops Module (`/api/areas`, `/api/shops`)

### `POST /api/areas/`
* **Purpose:** Defines a new geographical area for field operations.
* **Roles:** Admin only.
* **How to Test:** Provide the area details.
```json
{
  "name": "North District",
  "description": "Northern metropolitan zones"
}
```

### `GET /api/areas/`
* **Purpose:** Lists all defined areas.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Execute to view all areas.

### `PATCH /api/areas/{area_id}/assign`
* **Purpose:** Assigns a specific field salesperson to an area.
* **Roles:** Admin only.
* **How to Test:** Provide the `area_id` and the `user_id` of the sales agent.
```json
{
  "user_id": 2
}
```

### `POST /api/shops/`
* **Purpose:** Adds a new shop (potential client) to the system, usually within an area.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Provide the shop details.
```json
{
  "name": "Tech Hardware Store",
  "address": "456 Tech Ave, City",
  "contact_person": "John Doe",
  "phone": "5551234567",
  "email": "shop@techhardware.com"
}
```

### `GET /api/shops/`
* **Purpose:** Lists all registered shops.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Execute to view the shops.

### `PATCH /api/shops/{shop_id}`
* **Purpose:** Updates shop details.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Provide `shop_id` and updated fields.
```json
{
  "contact_person": "Jane Doe",
  "phone": "5559876543"
}
```

### `DELETE /api/shops/{shop_id}`
* **Purpose:** Deletes a shop.
* **Business Rule:** A shop **cannot** be deleted if it has been converted to a Client (matching email/phone).
* **Roles:** Admin only.
* **How to Test:** Delete a shop not linked to a client. Then try to delete a shop whose email/phone matches an active client to verify the `400 Bad Request` error.

---

## 5. Visits Module (`/api/visits`)

### `POST /api/visits/`
* **Purpose:** Logs a field visit to a shop by a salesperson. Can include photo uploads.
* **Business Rule:** Prevents duplicate visits by the same user to the same shop on the same day.
* **Roles:** Admin, Sales.
* **How to Test:** Provide the visit details.
```json
{
  "shop_id": 1,
  "status": "COMPLETED",
  "notes": "Discussed new product catalog. Owner seemed interested."
}
```

### `GET /api/visits/`
* **Purpose:** Lists visits, with optional filtering by `user_id` or `shop_id`.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Execute to see visits. Use query parameters to filter.

### `PATCH /api/visits/{visit_id}`
* **Purpose:** Updates a visit (e.g., changing status from SCHEDULED to COMPLETED).
* **Roles:** Admin, Sales.
* **How to Test:** Provide `visit_id` and the new `status` or updated `notes`.
```json
{
  "status": "COMPLETED",
  "notes": "Follow-up meeting completed."
}
```

*(Note: There is intentionally no DELETE endpoint for Visits to preserve audit history.)*

---

## 6. Clients Module (`/api/clients`)

### `POST /api/clients/`
* **Purpose:** Creates a new Client. This represents a successful conversion from a Shop/prospect.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Provide the client details.
```json
{
  "name": "Acme Corp",
  "email": "contact@acmecorp.com",
  "phone": "18005551234",
  "organization": "Acme Corporation Inc."
}
```

### `GET /api/clients/`
* **Purpose:** Retrieves a paginated, searchable list of active clients.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Execute to view clients. Note that inactive (soft-deleted) clients are hidden by default.

### `GET /api/clients/{client_id}`
* **Purpose:** Retrieves full details for a specific client.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Provide the `client_id`.

### `PATCH /api/clients/{client_id}`
* **Purpose:** Updates client information.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Provide `client_id` and fields to update.
```json
{
  "phone": "18005559999",
  "organization": "Acme Global Corp"
}
```

### `DELETE /api/clients/{client_id}`
* **Purpose:** Soft deletes a client.
* **Business Rule:** Sets `is_active = False` rather than removing the database row.
* **Roles:** Admin only.
* **How to Test:** Authenticate as an Admin, execute the deletion, then verify the client no longer appears in `GET /api/clients/`.

### `POST /api/clients/{client_id}/assign-pm`
* **Purpose:** Manually overrides or assigns a Project Manager to a client. (Note: standard assignment triggers automatically upon payment verification).
* **Roles:** Admin only.
* **How to Test:** Provide the `client_id` and the new `pm_id` in the JSON body.
```json
{
  "pm_id": 3
}
```

---

## 7. Payments Module (`/api/payments`) *(New Flow)*

### `POST /api/clients/{client_id}/payments/generate-qr`
* **Purpose:** Generates a payment request (and QR code) for a specific client.
* **Roles:** Admin, Sales, PMs.
* **How to Test:** Provide the `client_id` and the payment `amount`. Returns a mock QR code string and creates a `PENDING` payment record.

### `PATCH /api/payments/{payment_id}/verify`
* **Purpose:** Verifies a payment.
* **Business Rule:** This is **transactional** and **idempotent**. Verifying a payment automatically triggers the backend to assign a Project Manager (`pm_id`) to the client and logs it in `ClientPMHistory`. If already verified, it returns without error but skips assignment.
* **Roles:** Admin only.
* **How to Test:** Provide the `payment_id` of a pending payment. Check the client record afterward to confirm a `pm_id` was automatically assigned.

### `POST /api/payments/{payment_id}/send-invoice-whatsapp`
* **Purpose:** Simulates sending an invoice via WhatsApp for a verified payment.
* **Roles:** Admin only.
* **How to Test:** Execute on a verified `payment_id`. Should fail if the payment is still `PENDING`.

---

## 8. Meetings Module (`/api/clients/{client_id}/meetings`)

### `POST /api/clients/{client_id}/meetings`
* **Purpose:** Schedules a meeting with a client.
* **Business Rule:** PMs can only schedule meetings for clients assigned to them.
* **Roles:** Admin, PMs.
* **How to Test:** Provide the meeting details.
```json
{
  "title": "Initial Consultation",
  "content": "Discussing project requirements and timelines.",
  "date": "2026-03-05T10:00:00Z"
}
```

### `GET /api/clients/{client_id}/meetings`
* **Purpose:** Lists all meetings for a specific client.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Provide the `client_id`.

### `PATCH /api/clients/meetings/{meeting_id}`
* **Purpose:** Updates meeting details.
* **Roles:** Admin, PMs.
* **How to Test:** Provide `meeting_id` and updated summary/agenda.
```json
{
  "content": "Updated Agenda: Discussing revised budget."
}
```

### `POST /api/clients/meetings/{meeting_id}/cancel`
* **Purpose:** Cancels a meeting functionally.
* **Roles:** Admin, PMs.
* **How to Test:** Provide `meeting_id` and a cancellation reason.
```json
{
  "reason": "Client requested to reschedule for next week."
}
```

### `DELETE /api/clients/meetings/{meeting_id}`
* **Purpose:** Hard deletes a wrongly created meeting entry.
* **Business Rule:** Restricted to Admins, OR the PM currently assigned to the client.
* **Roles:** Admin, PMs.
* **How to Test:** Attempt deletion. Should succeed if you are Admin or the client's PM, fail otherwise.

### `POST /api/clients/meetings/{meeting_id}/import-summary`
* **Purpose:** Imports meeting transcription/notes from Google Meet.
* **Roles:** Admin, PMs.
* **How to Test:** Provide `meeting_id`. It updates the meeting content with mock Google Meet data and marks it `COMPLETED`.

---

## 9. Issues Module (`/api/clients/issues`, `/api/clients/{client_id}/issues`)

### `GET /api/clients/issues`
* **Purpose:** Global issue search. Pulls all issues across all clients with optional filters via query parameters.
* **Business Rule:** PMs are restricted to only viewing issues that belong to their assigned clients. Admins can see all.
* **Roles:** Admin, PMs.
* **How to Test:** Use the query parameters (like `status`, `severity`, or `client_id`) to filter the global issue list.

### `POST /api/clients/{client_id}/issues`
* **Purpose:** Logs a problem or support ticket for a client.
* **Business Rule:** PMs can only log issues for their own clients.
* **Roles:** Admin, PMs.
* **How to Test:** Provide the issue details.
```json
{
  "title": "Login Error",
  "description": "Client cannot access the portal using their new credentials.",
  "severity": "HIGH"
}
```

### `GET /api/clients/{client_id}/issues`
* **Purpose:** Lists all issues reported for a client.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Provide `client_id`.

### `PATCH /api/clients/issues/{issue_id}`
* **Purpose:** Updates issue details or status (e.g., marking it `RESOLVED`).
* **Roles:** Admin, PMs.
* **How to Test:** Provide `issue_id` and change the `status`.
```json
{
  "status": "RESOLVED",
  "resolution_notes": "Reset password and verified access."
}
```

*(Note: There is intentionally no DELETE endpoint for Issues.)*

---

## 10. Feedback Module (`/api/clients/{client_id}/feedback`)

### `POST /api/clients/{client_id}/feedback`
* **Purpose:** Submits client feedback/ratings. Can be anonymous.
* **Roles:** Public / Any authenticated user.
* **How to Test:** Provide the `client_id` in the URL and feedback details in the body.
```json
{
  "rating": 5,
  "comments": "Excellent service and quick turnaround."
}
```

### `GET /api/clients/{client_id}/feedback`
* **Purpose:** Views all submitted feedback for a given client.
* **Roles:** Admin, PMs.
* **How to Test:** Provide the `client_id` in the URL to view the feedback list.

### `POST /api/public/feedback/{token}`
* **Purpose:** Secure public endpoint for clients to submit feedback without a login.
* **Business Rule:** Expects a signed JWT `token` (valid for 30 days) that explicitly encodes the `client_id`. This prevents random probing/spam inputs.
* **Roles:** Public (with Token).
* **How to Test:** Generate a token programmatically (or from an email link), paste it into the URL param, and submit the JSON body.
```json
{
  "rating": 5,
  "comments": "Excellent service!"
}
```

*(Note: There is intentionally no DELETE endpoint for Feedback.)*

---

## 11. HR Payroll & Incentives (`/api/hrm`, `/api/incentives`)

### `POST /api/hrm/salary/generate`
* **Purpose:** Generates a salary slip for an employee for a specific month.
* **Roles:** Admin only.
* **How to Test:** Provide the payroll details.
```json
{
  "employee_id": 2,
  "month": "2026-03",
  "deduction_amount": 0.0
}
```

### `GET /api/hrm/salary/{employee_id}`
* **Purpose:** Retrieves generated salary slips for an employee.
* **Roles:** Admin, PMs.
* **How to Test:** Provide `employee_id`.

### `POST /api/incentives/slabs`
* **Purpose:** Defines rules for bonus payouts (e.g., "Hit 50% of target = ₹500 per unit").
* **Roles:** Admin only.
* **How to Test:** Provide the slab definition details.
```json
{
  "min_percentage": 50,
  "amount_per_unit": 500.0
}
```

### `POST /api/incentives/calculate`
* **Purpose:** Automatically calculates bonuses earned by compiling Client conversions (Sales) or completions (PMs).
* **Roles:** Admin only.
* **How to Test:** Provide the calculation lookup parameters.
```json
{
  "employee_id": 2,
  "period": "2026-03"
}
```

---

## 12. Reports & Dashboards (`/api/reports`)

### `GET /api/reports/dashboard`
* **Purpose:** Aggregates high-level metrics for the main screen.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Execute without payloads. Verify it returns `total_clients`, `open_issues`, and activity statistics.

---

## 13. Activity Logs (`/api/activity-logs`)

### `GET /api/activity-logs/`
* **Purpose:** Provides a read-only audit trail of who did what (creates, updates, soft-deletes).
* **Roles:** Admin only.
* **How to Test:** Execute to see a history array detailing timestamp, user ID, action type, and old/new data snapshots.

*(Note: Activity Logs cannot be modified or deleted by design.)*
