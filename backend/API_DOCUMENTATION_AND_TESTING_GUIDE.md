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
* **How to Test:** Expand the endpoint, click "Try it out", provide `email`, `name`, `password`, `phone`, and `role` (e.g., `ADMIN`, `SALES`, `PROJECT_MANAGER`), and execute. Note the returned `id` for employee mapping later.

### `POST /api/auth/login`
* **Purpose:** Authenticates a user and returns JWT tokens (`access_token` and `refresh_token`).
* **Roles:** Public (Unauthenticated)
* **How to Test:** Enter `username` (email) and `password` in the form. The response body contains the tokens. Swagger uses this internally when you use the "Authorize" button.

### `POST /api/auth/refresh`
* **Purpose:** Exchanges a valid `refresh_token` for a new `access_token` without requiring the user to log in again.
* **Roles:** Public (requires a valid refresh token in the body)
* **How to Test:** Provide the `refresh_token` string obtained from the login response.

---

## 2. Users Module (`/api/users`)

### `GET /api/users/me`
* **Purpose:** Returns the profile information of the currently authenticated user.
* **Roles:** Any authenticated user.
* **How to Test:** Ensure you are authorized via Swagger, then execute. It returns your user details based on the token.

### `PATCH /api/users/me`
* **Purpose:** Allows the currently authenticated user to update their own profile information (name, phone).
* **Roles:** Any authenticated user.
* **How to Test:** Provide updated string values for `name` or `phone`.

### `GET /api/users/`
* **Purpose:** Lists all users in the system (used primarily by Admins for management).
* **Roles:** Admin only.
* **How to Test:** Execute to see an array of all registered users.

### `PATCH /api/users/{user_id}/role`
* **Purpose:** Changes the role of a specific user.
* **Roles:** Admin only.
* **How to Test:** Provide the `user_id` and the new `role` string (e.g., `PROJECT_MANAGER`).

---

## 3. Employees Module (`/api/employees`)

### `POST /api/employees/`
* **Purpose:** Creates an employee record linking HR details (salary, department, target) to a system User account.
* **Roles:** Admin only.
* **How to Test:** Provide `employee_code`, `joining_date`, `base_salary`, `target`, `department`, and crucially, the `user_id` of a registered user.

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

### `GET /api/employees/{employee_id}/id-card`
* **Purpose:** Generates a digital ID card for the employee.
* **Roles:** Admin, or the Employee themselves.
* **How to Test:** Provide the `employee_id`. The system returns formatted ID card data (or triggers a PDF generation if fully implemented).

---

## 4. Areas & Shops Module (`/api/areas`, `/api/shops`)

### `POST /api/areas/`
* **Purpose:** Defines a new geographical area for field operations.
* **Roles:** Admin only.
* **How to Test:** Provide the `name` of the area (e.g., "North District").

### `GET /api/areas/`
* **Purpose:** Lists all defined areas.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Execute to view all areas.

### `PATCH /api/areas/{area_id}/assign`
* **Purpose:** Assigns a specific field salesperson to an area.
* **Roles:** Admin only.
* **How to Test:** Provide the `area_id` and the `user_id` of the sales agent.

### `POST /api/shops/`
* **Purpose:** Adds a new shop (potential client) to the system, usually within an area.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Provide shop `name`, `address`, `contact_person`, `phone`, `email`.

### `GET /api/shops/`
* **Purpose:** Lists all registered shops.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Execute to view the shops.

### `PATCH /api/shops/{shop_id}`
* **Purpose:** Updates shop details.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Provide `shop_id` and updated fields.

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
* **How to Test:** Provide the `shop_id`, `status` (`SCHEDULED`, `COMPLETED`), `notes`, and optionally upload an image file.

### `GET /api/visits/`
* **Purpose:** Lists visits, with optional filtering by `user_id` or `shop_id`.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Execute to see visits. Use query parameters to filter.

### `PATCH /api/visits/{visit_id}`
* **Purpose:** Updates a visit (e.g., changing status from SCHEDULED to COMPLETED).
* **Roles:** Admin, Sales.
* **How to Test:** Provide `visit_id` and the new `status` or updated `notes`.

*(Note: There is intentionally no DELETE endpoint for Visits to preserve audit history.)*

---

## 6. Clients Module (`/api/clients`)

### `POST /api/clients/`
* **Purpose:** Creates a new Client. This represents a successful conversion from a Shop/prospect.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Provide `name`, `email` (must be unique), `phone`, `organization`.

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

### `DELETE /api/clients/{client_id}`
* **Purpose:** Soft deletes a client.
* **Business Rule:** Sets `is_active = False` rather than removing the database row.
* **Roles:** Admin only.
* **How to Test:** Authenticate as an Admin, execute the deletion, then verify the client no longer appears in `GET /api/clients/`.

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
* **How to Test:** Provide `client_id`, `title`, `content` (agenda), and `date`.

### `GET /api/clients/{client_id}/meetings`
* **Purpose:** Lists all meetings for a specific client.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Provide the `client_id`.

### `PATCH /api/meetings/{meeting_id}`
* **Purpose:** Updates meeting details.
* **Roles:** Admin, PMs.
* **How to Test:** Provide `meeting_id` and updated summary/agenda.

### `POST /api/meetings/{meeting_id}/cancel`
* **Purpose:** Cancels a meeting functionally.
* **Roles:** Admin, PMs.
* **How to Test:** Provide `meeting_id` and a `reason` (e.g., "Client unavailable").

### `DELETE /api/meetings/{meeting_id}`
* **Purpose:** Hard deletes a wrongly created meeting entry.
* **Business Rule:** Restricted to Admins, OR the PM currently assigned to the client.
* **Roles:** Admin, PMs.
* **How to Test:** Attempt deletion. Should succeed if you are Admin or the client's PM, fail otherwise.

### `POST /api/meetings/{meeting_id}/import-summary`
* **Purpose:** Imports meeting transcription/notes from Google Meet.
* **Roles:** Admin, PMs.
* **How to Test:** Provide `meeting_id`. It updates the meeting content with mock Google Meet data and marks it `COMPLETED`.

---

## 9. Issues Module (`/api/clients/{client_id}/issues`)

### `POST /api/clients/{client_id}/issues`
* **Purpose:** Logs a problem or support ticket for a client.
* **Business Rule:** PMs can only log issues for their own clients.
* **Roles:** Admin, PMs.
* **How to Test:** Provide `client_id`, `title`, `description`.

### `GET /api/clients/{client_id}/issues`
* **Purpose:** Lists all issues reported for a client.
* **Roles:** Admin, PMs, Sales.
* **How to Test:** Provide `client_id`.

### `PATCH /api/issues/{issue_id}`
* **Purpose:** Updates issue details or status (e.g., marking it `RESOLVED`).
* **Roles:** Admin, PMs.
* **How to Test:** Provide `issue_id` and change the `status`.

*(Note: There is intentionally no DELETE endpoint for Issues.)*

---

## 10. Feedback Module (`/api/feedback`)

### `POST /api/feedback/`
* **Purpose:** Submits client feedback/ratings. Can be anonymous.
* **Roles:** Public / Any authenticated user.
* **How to Test:** Provide a `rating` (1-5), optional `comments`, and link to a `client_id`.

### `GET /api/feedback/`
* **Purpose:** Views all submitted feedback.
* **Roles:** Admin, PMs.
* **How to Test:** Execute to view the feedback list.

*(Note: There is intentionally no DELETE endpoint for Feedback.)*

---

## 11. HR Payroll & Incentives (`/api/hrm`, `/api/incentives`)

### `POST /api/hrm/salary/generate`
* **Purpose:** Generates a salary slip for an employee for a specific month.
* **Roles:** Admin only.
* **How to Test:** Provide the `employee_id`, `month` (e.g., "2026-03"), and `deduction_amount`. Calculates final pay based on base salary minus deductions + incentives.

### `GET /api/hrm/salary/{employee_id}`
* **Purpose:** Retrieves generated salary slips for an employee.
* **Roles:** Admin, PMs.
* **How to Test:** Provide `employee_id`.

### `POST /api/incentives/slabs`
* **Purpose:** Defines rules for bonus payouts (e.g., "Hit 50% of target = ₹500 per unit").
* **Roles:** Admin only.
* **How to Test:** Provide `min_percentage` and `amount_per_unit`.

### `POST /api/incentives/calculate`
* **Purpose:** Automatically calculates bonuses earned by compiling Client conversions (Sales) or completions (PMs).
* **Roles:** Admin only.
* **How to Test:** Provide `employee_id` and `period` (e.g., "2026-03"). System queries the Client database to see how many were added/managed by the user that month and applies the Slabs.

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
