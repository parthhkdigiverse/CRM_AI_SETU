# CRM AI SETU - Comprehensive Frontend UI/UX Design Document

This document serves as the master blueprint for the frontend design of the CRM AI SETU web application. It outlines the visual language, layout principles, and pixel-perfect specifications for developers to build the complete user interface.

---

## 1. Global Design System (Tokens)

To ensure consistency, the frontend must strictly adhere to this Design System.

### 1.1 Colors
*   **Primary Brand:** Deep Indigo (`#4F46E5`) - Primary buttons, active nav items.
    *   Hover state: `#4338CA`
    *   Light background (e.g., tags, active nav items): `#EEF2FF`
*   **Secondary/Accent:** Vibrant Teal (`#0D9488`) - Used for success actions or conversion metrics.
*   **Neutral/Backgrounds:**
    *   App Background: `#F9FAFB` (Soft light gray, minimizes eye strain)
    *   Surface/Cards: `#FFFFFF` (Pure white)
    *   Borders: `#E5E7EB`
*   **Text Colors:**
    *   Primary Heading: `#111827` (Near black)
    *   Body Text: `#4B5563`
    *   Muted/Subtext: `#9CA3AF`
*   **Semantic Colors:**
    *   Success (Completed/Won): `#10B981`
    *   Warning (Pending/Issue): `#F59E0B`
    *   Danger (Lost/Delete/High Severity): `#EF4444`

### 1.2 Typography
*   **Primary Font Family:** `Inter` or `Roboto` (Sans-serif, highly legible for data-heavy apps).
*   **Font Weights:**
    *   Regular (400) for body text.
    *   Medium (500) for buttons and table headers.
    *   Semibold (600) for section titles and active navigation links.
*   **Sizes:**
    *   `h1`: 24px (Page Titles)
    *   `h2`: 18px (Card Titles)
    *   `body`: 14px (General text, tables)
    *   `small`: 12px (Subtext, badges)

### 1.3 Shadows & Borders (Glassmorphism Light)
*   **Border Radius:** `8px` for buttons and inputs, `12px` for large cards/modals.
*   **Card Shadow:** `0 4px 6px -1px rgba(0, 0, 0, 0.05)` — Cards should look like they are floating slightly off the background.
*   **Modals/Dropdowns Shadow:** `0 10px 15px -3px rgba(0, 0, 0, 0.1)` (Deeper shadow for emphasis).

---

## 2. Core Layout Architecture

The application uses an **App Shell Layout**, consisting of a fixed Sidebar and fixed Header, with a scrollable main content area.

### 2.1 The Sidebar (Left - Width: 250px)
*   **Background:** `#FFFFFF` with a slight right border (`#E5E7EB`).
*   **Header Logo:** "CRM AI SETU" in bold 18px text, aligned with an app icon.
*   **Navigation Structure:** (Collapsible accordions for cleaner look)
    *   📊 **Dashboard**
    *   🛡️ **Administration** (Users tracking)
    *   🗺️ **Field Operations** (Leads, Areas, Shops, Visits)
    *   💼 **Project Management** (Projects, Meetings)
    *   🤝 **Client Relations** (Clients, Feedback, Issues)
    *   💰 **HR & Payroll** (Salary, Leaves, Incentives)
    *   📈 **Reports & Analytics**
*   **Footer:** Pinned to bottom (Settings ⚙️, Logout 🚪).
*   **Interaction:** Active links have text color `#4F46E5`, a background of `#EEF2FF`, and a bold weight.

### 2.2 The Top Navbar (Header - Height: 64px)
*   **Background:** `#FFFFFF` blurring into the app background (backdrop-filter: blur).
*   **Left Component:** Dynamic Breadcrumbs (e.g., `Field Operations > Leads`).
*   **Center Component:** Search Bar (Width: 300px, grey background `#F3F4F6`, magnifying glass icon inside left).
*   **Right Component:**
    *   `+ Add New` Button (Primary Indigo design).
    *   Notification Bell (With red dot badge).
    *   User Profile Dropdown (Circular Avatar + "Admin").

---

## 3. Page Templates & Component Design

### 3.1 Data Tables (List Views)
Used for viewing Leads, Projects, Employees, etc.
*   **Toolbar:** Sits above the table. Contains "Filter", "Export", and "Search within table" inputs.
*   **Headers:** Light grey background `#F9FAFB`, uppercase text, 12px font size.
*   **Rows:**
    *   White background. Slight greying effect on hover (`#F3F4F6`) to help users track lines horizontally.
*   **Status Badges (Pills):**
    *   Status indicators (e.g., `NEW`, `CONVERTED`, `PLANNED`) use rounded pill badges.
    *   Example: `CONVERTED` uses a green background (`#D1FAE5`) with dark green text (`#065F46`).
*   **Actions Column:** Far right side of the row. Contains minimal icons: View (👁️), Edit (✏️), Delete (🗑️).

### 3.2 Forms (Create/Edit Views)
Used when adding a new Client, Project, or Employee.
*   **Layout:** Displayed in a sliding side-panel (drawer) floating over the main view, OR as a centered Modal with a dark backdrop overlay.
*   **Inputs:** Height `40px`. Border `#D1D5DB`. On focus, the border turns Indigo (`#4F46E5`) with a subtle outer glow (box-shadow).
*   **Labels:** Small, bold, positioned above the input field.
*   **Action Buttons:** Bottom right alignment. "Cancel" (Ghost button, gray text) and "Submit" (Solid Indigo button).

### 3.3 The Main Dashboard
*(Refer to DASHBOARD_UI_UX_DESIGN.md for specific content layout of rows and columns).*
*   **Empty States:** If a section of the dashboard (like "Pending Issues") has no data, show a friendly 100px SVG illustration (like a checkmark on a clipboard) with pale gray text saying "No issues to report! Great job."

### 3.4 Kanban Boards (Optional View for Leads/Projects)
Instead of just a table, allow users to view Leads in a Kanban board layout.
*   **Columns:** E.g., `New | Contacted | Meeting Set | Converted`.
*   **Cards:** Each Lead is a white card with a subtle shadow. Cards display Lead Name, a small phone icon, and a tag showing the lead source (e.g., `Website`). 
*   **Interaction:** Users should be able to drag and drop cards between columns to instantly trigger a status update in the backend.

---

## 5. Page-by-Page UI Specifications

This section breaks down the specific layout and components required for every major page inside the CRM, beyond just the Dashboard.

### 5.1 Administration: Users & Roles Page
**Purpose:** Manage system access, employee mapping, and role assignments.
*   **Top Bar:** "Add User" button.
*   **Main View:** Data Table.
    *   **Columns:** Name, Email, Role (Styled Badge), Employee Status (Linked/Unlinked), Actions.
    *   **Role Badges:** `[ADMIN]` (Red border), `[PROJECT_MANAGER]` (Blue border), `[SALES]` (Green border).
*   **Action Panel (Right-Slide Drawer):** When clicking "Edit", a side drawer slides in from the right to update the user's details or change their role dropdown without leaving the page.

### 5.2 Field Operations: Leads Page
**Purpose:** Manage new customer inquiries and progress them through the sales funnel.
*   **Top Bar:** "View Toggle" (Icon buttons to switch between Table View and Kanban View). "Add Lead" button.
*   **Kanban View (Default):**
    *   Columns map to Lead Status (`NEW`, `CONTACTED`, `MEETING_SET`, `CONVERTED`, `LOST`).
    *   Cards show Lead Name, Source, assigned Salesperson Avatar, and a "Convert to Client" quick-action button if in the final column.
*   **Table View:** Standard data table with bulk selection checkboxes to assign area/shops to multiple leads at once.
*   **Slide Drawer (Lead Details):** Clicking a lead opens a drawer showing full history, notes, and an "Add Note" text area.

### 5.3 Field Operations: Areas & Shops Page
**Purpose:** Geographical tracking for Telesales/Field Sales.
*   **Top Bar:** "Add Area/Shop" button, plus a "Map View" toggle.
*   **Main View (Split Pane):**
    *   **Left Pane (30%):** A searchable, clickable list of **Areas** (e.g., "North District").
    *   **Right Pane (70%):** A data table showing all **Shops** linked to the Area selected on the left.
    *   **Shop Columns:** Shop Name, Owner, Phone, Last Visit Date.

### 5.4 Client Relations: Clients Page
**Purpose:** Central repository for all converted accounts.
*   **Main View:** Data Table (Grid of Client Cards also acceptable if preferred).
    *   **Columns:** Company Name, Primary Contact, Email, Total Projects (Number), LTV (Lifetime Value).
*   **Client Detail View (Full Page Transition):** Clicking a client doesn't open a drawer; it navigates to a dedicated Client Profile Page.
    *   **Header:** Large typography with Company Name and Contact Info.
    *   **Tabs:** Let users switch between `Overview`, `Linked Projects`, `Feedback History`, and `Invoices/Billing`.

### 5.5 Project Management: Projects Page
**Purpose:** High-level overview of delivery and execution.
*   **Top Bar:** Status filters (Pills: `All`, `Planned`, `Ongoing`, `Completed`, `On Hold`). "Create Project" button.
*   **Main View:** Visual "Progress" Table.
    *   **Columns:** Project Name, Client, Assigned PM (User Avatar), Timeline (Start/End date), Status, Budget.
    *   *Special UI Element:* Include a mini **Progress Bar** summarizing completed meetings/resolved issues vs total.
*   **Project Detail View (Full Page Transition):**
    *   Similar to the Client Profile Page. Contains Tabs for `Overview`, `Meetings`, `Issues`, and `Financials`.

### 5.6 Project Management: Meetings & Issues
*(Can be tabs inside the Project Detail View, or dedicated global overview pages).*
*   **Global Issues View:** A unified table showing *all* open issues across *all* projects.
    *   **Highlighting:** Rows containing `HIGH` severity issues have a very faint red background (`#FEF2F2`) to draw immediate eye attention.
    *   **Columns:** Issue Title, Severity Badge, Status Badge, Associated Project, Assigned PM.

### 5.7 HR & Payroll: Employees Page
**Purpose:** Manage staff details, targets, and base salaries.
*   **Main View:** Data Table.
    *   **Columns:** Employee Code, Full Name, Department, Base Salary, Target Amount, Joining Date.
    *   **Quick Action:** A circular "Generate Referral Code" icon button in the actions column.

### 5.8 HR & Payroll: Salary & Leaves
**Purpose:** Process monthly payroll and manage absences.
*   **Top Bar:** A glowing "Generate Payroll (Current Month)" primary button. Month/Year date picker dropdown.
*   **Main View (Split Screen):**
    *   **Top Half:** A summary metrics strip (Total Payroll Cost, Incentives Disbursed, Pending Leaves).
    *   **Bottom Half:** A table of Salary Slips generated for the selected month.
    *   **Columns:** Employee Name, Base, Deductions (Unpaid Leaves), Incentives Earned, Final Payout, Status (`PAID`/`PENDING`).
    *   **Action:** A "Download PDF" icon button on each row to export the salary slip.

### 5.9 Reports & Analytics Page
**Purpose:** Deep dive into system performance beyond the Dashboard.
*   **Layout:** A masonry grid layout allowing users to drag and drop report widgets.
*   **Widgets:**
    *   **Sales Performance (Bar Chart):** Leads converted per sales agent this quarter.
    *   **Revenue Forecast (Line Graph):** Projected revenue based on Ongoing project budgets.
    *   **Issue Resolution Time (Heatmap):** Average days to close an issue, broken down by Project Manager.
*   **Global Filter:** A sticky top bar with a "Date Range Picker" (e.g., `Last 30 Days`, `This Quarter`, `Custom Range`) that automatically refreshes all charts below it.

---

## 6. Mobile Responsiveness Strategy
*   **Breakpoints:** UI transforms at tablet (768px) and mobile (480px) widths.
*   **Sidebar:** Hides completely off-canvas on tablet/mobile. Users open it via a "Hamburger Menu" (≡) spanning from the left.
*   **Tables:** Standard tables shrink poorly on phones. On mobile, tables transform into a "Card List" (each table row becomes a stacked vertical card).
*   **Grid Layouts:** Dashboard grids that are 4-columns wide on desktop become 1-column wide (stacked vertically) on mobile devices.

---

## 7. Data Deletion Rules (API Enforcement)

To maintain data integrity and audit trails, the backend APIs enforce the following strict deletion rules. The frontend UI should reflect these restrictions by hiding or disabling "Delete" buttons in unauthorized contexts:

*   **Clients (`DELETE /api/clients/{id}`):** Soft delete only (`is_active = false`). Only strictly permitted for **Admins**.
*   **Meeting Summaries (`DELETE /api/clients/meetings/{id}`):** Can be deleted only by an **Admin** or the **Project Manager (Creator)**. *Note: Functional cancellations should use the `/cancel` endpoint; deletion is reserved only for wrongly created entries.*
*   **Shops (`DELETE /api/shops/{id}`):** Can be deleted only if the shop has **not** been converted to a Client (verified by matching email or phone).
*   **No Deletion Supported:** Deletion is strictly prohibited for **Issues, Visits, Employees, Feedback, Payments, Salary, Incentives, and Activity Logs** to preserve historical and financial reporting integrity.
