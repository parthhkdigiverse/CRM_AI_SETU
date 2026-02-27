# CRM AI SETU - API Status & Missing Features Report

Based on your detailed requirements, a comprehensive review of the project codebase (`backend/app/modules`) has been conducted. Below is the summary of what is fully implemented, partially implemented, and what is left to be created or modified.

## 1. Fully Implemented Features ❤️
The following features have their APIs and Logic thoroughly created:
- **Roles:** All roles (`ADMIN`, `SALES`, `TELESALES`, `PROJECT_MANAGER`, `PROJECT_MANAGER_AND_SALES`, `CLIENT`) are correctly defined.
- **Admin Area Assignment:** `areas/router.py` handles area creation and assignment to sales persons.
- **Telesales Workflow:** Telesales can process shop visits without uploading photos (photo is strictly optional in the API).
- **Client Issues:** `issues/router.py` fully supports adding/managing client issues by sales or managers.
- **PM Auto Distribution:** `payments/service.py` automatically load-balances and assigns the PM with the fewest active clients after payment verification.
- **Meeting Scheduler:** `meetings/router.py` handles PM schedules, cancellations, and reschedules. `employees/router.py` fetches PM availability calendar slots.
- **Meeting Summary (Google Meet):** `meetings/router.py` contains `import-summary` which is pre-configured to mock fetch a Google Meet summary.
- **Client Feedback:** `feedback/router.py` accepts and lists client feedback.
- **Admin Reports:** `reports/router.py` supplies dashboard statistics for all employees.
- **Employee ID Card:** `employees/router.py` contains an endpoint to automatically generate ID card mock URLs.
- **Salary Calculation:** `salary/router.py` has API endpoints for processing leaves and calculating salary slips.
- **Incentive Calculation:** `incentives/router.py` processes targets, slabs, and final incentive calculation for sales.
- **Referral Code Generation:** `employees/router.py` contains the API to generate specific referral codes.

---

## 2. Partially Implemented / Needs Modification ⚠️
These features are present but need adjustments to perfectly match your exact specifications:

### A. Sales Visit Status & Remarks
* **Current:** Shops and Visits are created, and photos can be uploaded via `POST /visits`. However, the current status choices are only `SCHEDULED`, `COMPLETED`, `MISSED`, `CANCELLED`. It also uses a generic `notes` field.
* **Missing/Left:** 
  1. We need to update `VisitStatus` enum to include specific choices: `SATISFIED`, `ACCEPT`, `DECLINE`, `TAKE_TIME_TO_THINK`.
  2. The existing `notes` field should be renamed to `remarks`. This `remarks` field will be specifically used to capture the details of the visit, and especially the "why" if the client declines.

### B. Payment -> Bill Generation -> WhatsApp
* **Current:** Payments QR generation (`POST /payments/generate-qr`), Payment Verification (`PATCH /payments/{id}/verify`), and a mock WhatsApp sending endpoint (`POST /payments/{id}/send-invoice-whatsapp`) are present.
* **Missing/Left:**
  1. Automatic Bill/Invoice schema is not fully dedicated; it is lumped into `Payment` verification. We will create a dedicated `/billing` generator.
  2. The workflow currently expects the Sales rep to manually create a `Client` before generating the Payment QR. We need an API that takes a `Shop ID`, generates the Bill/Payment QR, and **automatically registers** them into the `clients` table entirely in the background.
  3. **WhatsApp API Integration Setup:** The official WhatsApp Cloud API is not completely free for unlimited template messages (it has a free tier for a certain number of service conversations, but business-initiated templates often carry a small cost per message). We will need to set up a real provider (like Meta's official Cloud API, Twilio, or Wati) and securely store the API keys in `.env`. We will implement the actual API call logic replacing the current mock `print` statement.

### C. Profile Management
* **Current:** We have `employees` and `users` routers to fetch details. We have `PATCH /users/{user_id}/role` to change a user's role (Change Position).
* **Missing/Left:**
  1. No explicit `GET /profile` or `PATCH /profile` endpoint for a user to see and update their own specific details (password, phone number, etc.). They have to rely on generic `users` or `employees` reading endpoints right now, which are Admin-only.

---

## 3. APIs Left to be Created / Modified (TODO List) 📝

Based on the updated frontend requirements, the following entirely new modules or significant modifications are needed:

1. **Update `Visit` Model & Router:**
   - Modify `app/modules/visits/models.py` enum to have `SATISFIED, ACCEPT, DECLINE, TAKE_TIME_TO_THINK`.
   - Add `decline_remarks` string column to `Visit` model.
2. **Shop to Client Auto-Conversion Flow:**
   - Create a specific API in `payments` or `billing` that takes a `Shop ID`, generates the Bill/Payment QR, and **automatically registers** them into the `clients` table entirely in the background. Currently, `generate_payment_qr` requires a `client_id` directly.
3. **Verify Webhook for WhatsApp:**
   - Connect the mock `/send-invoice-whatsapp` to the actual third-party WhatsApp Business API provider when ready.
4. **Projects Module:**
   - **Missing entirely.** Need a new `projects` module (`models.py`, `schemas.py`, `router.py`, `service.py`) to handle creating and managing projects. This is required for Admin, Sales, Telesales, and PM roles on the frontend.
5. **To-Do Module:**
   - **Missing entirely.** Need a new `todos` module. This allows users to create daily tasks. Required for all roles.
6. **Timetable / Calendar Features:**
   - **Needs Extension.** We have meeting schedules, but we may need a dedicated `timetable` or `calendar` endpoint to aggregate Visits, Meetings, To-Dos, and Leaves into a single timeline response for the frontend calendar view.
7. **Notifications API:**
   - **Missing router/endpoint.** We have an internal `notifications/service.py` to send emails, but no `notifications/router.py` to fetch a user's notifications (e.g., `GET /notifications` to mark as read, see recent alerts). Required for the Admin.
8. **My Clients / Client Filtering for PM:**
   - Ensure the `GET /clients` endpoint properly filters by `pm_id` automatically when a Project Manager calls it, to fulfill the "my clients" frontend view.
9. **User & Client Feedback Segmentation:**
   - Check `feedback/router.py`. Ensure we can differentiate between "User" (internal employee) feedback and "Client" feedback based on the frontend requirement. 
10. **Auth / Profile Router:**
    - Create a dedicated `GET /auth/profile` and `PATCH /auth/profile` so users can view and update their own profile data without needing Admin access.
