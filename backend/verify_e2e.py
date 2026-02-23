import requests
import time
from datetime import datetime
import json

BASE_URL = "http://127.0.0.1:8123/api"
TOKEN = None

# Helper to print step results
def print_step(name, success, info=""):
    status = "PASS" if success else "FAIL"
    print(f"{status} | {name} | {info}")
    if not success:
        print("Terminating E2E flow due to failure.")
        exit(1)

def get_headers():
    if TOKEN:
        return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    return {"Content-Type": "application/json"}

# ---------------------------------------------------------
# Step 1: Authentication
# ---------------------------------------------------------
print("\n--- Starting E2E Verification Flow ---")
try:
    auth_data = {"username": "admin@example.com", "password": "password123"}
    r = requests.post(f"{BASE_URL}/auth/login", data=auth_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r.status_code == 200:
        TOKEN = r.json().get("access_token")
        print_step("Admin Login", True)
    else:
        print_step("Admin Login", False, f"Status: {r.status_code} - {r.text}")
except Exception as e:
    print_step("Admin Login", False, str(e))

# ---------------------------------------------------------
# Step 2: User Registration & Employee Creation
# ---------------------------------------------------------
sales_user_id = None
sales_emp_id = None
pm_user_id = None
pm_emp_id = None
timestamp = int(time.time())

# Register Sales User
sales_user_data = {
    "email": f"sales_{timestamp}@example.com",
    "name": f"E2E Sales {timestamp}",
    "password": "Password123!",
    "phone": f"98765{str(timestamp)[-5:]}",
    "role": "SALES",
    "is_active": True
}
r = requests.post(f"{BASE_URL}/auth/register", json=sales_user_data, headers=get_headers())
if r.status_code in [200, 201]:
    sales_user_id = r.json().get("id")
    print_step("Register Sales User", True, f"User ID: {sales_user_id}")
else:
    print_step("Register Sales User", False, r.text)

# Create Sales Employee
sales_emp_data = {
    "employee_code": f"SLS-{timestamp}",
    "joining_date": "2026-03-01",
    "base_salary": 50000.0,
    "target": 5,
    "department": "Sales",
    "user_id": sales_user_id
}
r = requests.post(f"{BASE_URL}/employees/", json=sales_emp_data, headers=get_headers())
if r.status_code in [200, 201]:
    sales_emp_id = r.json().get("id")
    print_step("Create Sales Employee", True, f"Employee ID: {sales_emp_id}")
else:
    print_step("Create Sales Employee", False, r.text)

# Register PM User
pm_user_data = {
    "email": f"pm_{timestamp}@example.com",
    "name": f"E2E PM {timestamp}",
    "password": "Password123!",
    "phone": f"88765{str(timestamp)[-5:]}",
    "role": "PROJECT_MANAGER",
    "is_active": True
}
r = requests.post(f"{BASE_URL}/auth/register", json=pm_user_data, headers=get_headers())
if r.status_code in [200, 201]:
    pm_user_id = r.json().get("id")
    print_step("Register PM User", True, f"User ID: {pm_user_id}")
else:
    print_step("Register PM User", False, r.text)

# Create PM Employee
pm_emp_data = {
    "employee_code": f"PM-{timestamp}",
    "joining_date": "2026-03-01",
    "base_salary": 80000.0,
    "target": 2,
    "department": "Engineering",
    "user_id": pm_user_id
}
r = requests.post(f"{BASE_URL}/employees/", json=pm_emp_data, headers=get_headers())
if r.status_code in [200, 201]:
    pm_emp_id = r.json().get("id")
    print_step("Create PM Employee", True, f"Employee ID: {pm_emp_id}")
else:
    print_step("Create PM Employee", False, r.text)

# ---------------------------------------------------------
# Step 3: Lead Creation
# ---------------------------------------------------------
lead_id = None
lead_data = {
    "name": f"E2E Tech Corp {timestamp}",
    "phone": f"11223{str(timestamp)[-5:]}",
    "source": "Website",
    "status": "NEW",
    "assigned_to": sales_emp_id
}
r = requests.post(f"{BASE_URL}/leads/", json=lead_data, headers=get_headers())
if r.status_code in [200, 201]:
    lead_id = r.json().get("id")
    print_step("Create Lead", True, f"ID: {lead_id}")
else:
    print_step("Create Lead", False, r.text)

# ---------------------------------------------------------
# Step 4: Client Conversion
# ---------------------------------------------------------
client_id = None
client_data = {
    "name": lead_data["name"],
    "email": f"contact_{timestamp}@e2etech.example",
    "phone": lead_data["phone"],
    "address": "123 E2E Lane",
    "company_name": lead_data["name"],
    "lead_id": lead_id
}
r = requests.post(f"{BASE_URL}/clients/", json=client_data, headers=get_headers())
if r.status_code in [200, 201]:
    client_id = r.json().get("id")
    print_step("Create/Convert Client", True, f"ID: {client_id}")
else:
    print_step("Create/Convert Client", False, r.text)

# ---------------------------------------------------------
# Step 5: Project Creation
# ---------------------------------------------------------
project_id = None
project_data = {
    "name": f"E2E Implementation {timestamp}",
    "client_id": client_id,
    "description": "Automated project scope",
    "status": "PLANNED",
    "start_date": "2026-03-01",
    "end_date": "2026-06-01",
    "budget": 150000.0
}
r = requests.post(f"{BASE_URL}/projects/", json=project_data, headers=get_headers())
if r.status_code in [200, 201]:
    project_id = r.json().get("id")
    assigned_pm = r.json().get("pm_id")
    print_step("Create Project (Auto-PM)", True, f"ID: {project_id}, Assigned PM: {assigned_pm}")
else:
    print_step("Create Project (Auto-PM)", False, r.text)

# ---------------------------------------------------------
# Step 6: Meetings and Issues
# ---------------------------------------------------------
meeting_data = {
    "title": "Kickoff Sync",
    "meeting_time": "2026-03-02T10:00:00Z",
    "mode": "ONLINE",
    "summary": "Automated kickoff note."
}
r = requests.post(f"{BASE_URL}/projects/{project_id}/meetings/", json=meeting_data, headers=get_headers())
if r.status_code in [200, 201]:
    print_step("Log Meeting", True, f"Meeting created for project {project_id}")
else:
    print_step("Log Meeting", False, r.text)

issue_data = {
    "title": "E2E Test Issue",
    "description": "Testing issue tracking.",
    "status": "OPEN",
    "severity": "LOW"
}
r = requests.post(f"{BASE_URL}/projects/{project_id}/issues/", json=issue_data, headers=get_headers())
if r.status_code in [200, 201]:
    print_step("Log Issue", True, f"Issue created for project {project_id}")
else:
    print_step("Log Issue", False, r.text)

# ---------------------------------------------------------
# Step 7: HR Operations
# ---------------------------------------------------------
salary_data = {
    "employee_id": sales_emp_id,
    "month": f"2026-{str((timestamp % 12) + 1).zfill(2)}", # Randomize month to avoid duplicate errors across reruns
    "deduction_amount": 0.0
}
r = requests.post(f"{BASE_URL}/hrm/salary/generate", json=salary_data, headers=get_headers())
if r.status_code in [200, 201]:
    print_step("Generate Salary", True, f"Slip ID: {r.json().get('id')}")
else:
    # 400 with 'Salary slip already exists' is acceptable if rerunning in the same month very quickly, but we randomize above.
    print_step("Generate Salary", False, r.text)

incentive_data = {
    "employee_id": sales_emp_id,
    "period": salary_data["month"]
}
r = requests.post(f"{BASE_URL}/incentives/calculate", json=incentive_data, headers=get_headers())
if r.status_code in [200, 201]:
    print_step("Calculate Incentive", True, f"Achieved: {r.json().get('achieved')}")
else:
    print_step("Calculate Incentive", False, r.text)

# ---------------------------------------------------------
# Step 8: Dashboard Verification
# ---------------------------------------------------------
r = requests.get(f"{BASE_URL}/reports/dashboard", headers=get_headers())
if r.status_code in [200, 201]:
    data = r.json()
    print_step("Fetch Dashboard", True, f"Projects: {data.get('total_projects')}, Mngd Employees: {data.get('total_employees')}")
else:
    print_step("Fetch Dashboard", False, r.text)

print("\n--- E2E Verification Completed Successfully ---")
