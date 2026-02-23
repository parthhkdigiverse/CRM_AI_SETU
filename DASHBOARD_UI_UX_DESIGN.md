# CRM AI SETU - Dashboard UI/UX Design Specification

This document outlines the theoretical UI/UX design for the CRM dashboard, focusing on layout, aesthetics, and user journey. No code is included—this serves as a blueprint for frontend developers or designers.

## 1. Overall Aesthetic & Theme
- **Design Style:** Modern, clean, and slightly glassmorphic. 
- **Color Palette:**
  - **Primary Color:** Deep Indigo (`#4F46E5`) for primary actions and highlights.
  - **Background:** Soft light gray (`#F9FAFB`) for the main content area to reduce eye strain, or a sleek dark mode (`#111827`).
  - **Sidebar/Navbar:** Crisp white (`#FFFFFF`) in light mode with subtle drop shadows (`box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1)`).
- **Typography:** **Inter** or **Roboto** for a highly legible, professional corporate feel. 

---

## 2. Layout Structure
The application will follow a classic, highly effective **Sidebar + Top Navbar** dashboard layout.

### A. The Sidebar (Left Navigation)
**Purpose:** Global navigation across all CRM modules. Fixed to the left side of the screen.
- **Header:** System logo ("CRM AI SETU") and a collapse button to toggle the sidebar to icons-only (saving screen space on smaller devices).
- **Navigation Links** (Structured with expandable sub-menus to keep the UI clean):
  - 📊 **Dashboard** (Main landing page)
  - 🛡️ **Administration**
    - Users & Roles (Managing system access and employee mapping)
  - 🗺️ **Field Operations** (Pre-sales & Ground activities)
    - Leads
    - Areas
    - Shops
    - Visits
  - 💼 **Project Management**
    - Projects
    - Meetings
  - 🤝 **Client Relations**
    - Clients
    - Feedback
    - Issues
  - 💰 **HR & Payroll**
    - Salary & Leaves (Including Incentives)
  - 📈 **Reports & Analytics**
- **Footer:** Pin these to the absolute bottom of the sidebar:
  - ⚙️ **Settings**
  - 🚪 **Logout**

### B. The Top Navbar (Header)
**Purpose:** Quick actions, contextual search, and user profile management. Fixed to the top, sitting to the right of the sidebar.
- **Left Side:** Breadcrumbs (e.g., `Home / Dashboard`) letting the user know exactly where they are.
- **Center:** A global **"Search anything..."** bar. Searching here auto-completes Leads, Clients, or Projects.
- **Right Side:**
  - **"Quick Add" Button (+):** A highly visible button to instantly add a New Lead, Meeting, or Issue without navigating away from the current page.
  - **Notifications Bell:** Displays a red dot badge (🔔) for new issues or pending PM assignments.
  - **User Profile:** A circular avatar, the user's name (e.g., `Admin User`), and a pill-shaped badge indicating their role (e.g., `[ADMIN]`, `[SALES]`). Clicking it opens a dropdown for Profile Preferences and Logout.

---

## 3. Main Dashboard Content Area
The core of the dashboard needs to provide an "at-a-glance" summary of the CRM's health. It should be divided into logical rows or grids.

### Row 1: Greeting & Date
- A friendly, dynamic greeting based on time of day: *"Good Morning, Admin! Here is what's happening today."*
- A live date string aligned to the right.

### Row 2: KPI "Quick Stat" Cards (Grid of 4)
Four elegantly styled cards summarizing critical data. Each card should have:
1. A descriptive title.
2. The primary large number.
3. A small green/red trend indicator (e.g., `↑ +12% from last month`).
4. A faded icon in the background for visual flair.
   - **Card 1: Total Active Projects** (Icon: Briefcase)
   - **Card 2: Total Clients** (Icon: Users)
   - **Card 3: New Leads** (Icon: Target)
   - **Card 4: Pending Issues** (Icon: Alert Triangle, highlighted in soft red if count > 0)

### Row 3: Data Visualization (Charts)
Two charts sitting side-by-side to visually break down the metrics.
- **Left Chart (Bar/Area Chart): Revenue or Project Completions over Time.** Showing the last 6 months of growth.
- **Right Chart (Doughnut/Pie Chart): Leads by Status.** A colorful ring chart broken down into `NEW`, `CONTACTED`, `CONVERTED`, and `LOST`. Hovering over a slice shows the exact number.

### Row 4: Actionable Lists (Bottom Half)
Two lists sitting side-by-side to drive immediate user action.
- **Left Panel: "Recent Activity / Upcoming Meetings"**
  - A scrollable, timeline-style list.
  - Shows things like: *"Meeting: Kickoff Sync at 10:00 AM"* or *"New Lead Added: E2E Tech Corporate"*.
- **Right Panel: "Projects Requiring Attention"**
  - A list of projects that either have **Open High-Severity Issues** or are **Unassigned (Missing a PM)**.
  - Each list item has a quick "View" button to jump straight into resolving the problem.

---

## 4. Micro-Interactions & UX Theory
- **Hover Effects:** Every clickable element (buttons, sidebar links, table rows) should subtly raise up (`transform: translateY(-2px)`) or slightly darken on hover to indicate interactivity.
- **Empty States:** If there are no leads or projects yet, don't show a blank chart. Show a friendly illustration with a button saying *"No projects yet. Create your first project!"*
- **Responsiveness:** On mobile or tablet, the Sidebar should completely hide behind a "Hamburger Menu" (≡) in the Navbar, and the Row 2 grid should stack vertically instead of side-by-side.
