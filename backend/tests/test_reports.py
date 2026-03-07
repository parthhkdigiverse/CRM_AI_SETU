import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Add backend to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
if backend_dir not in sys.path:
    # Insert at index 0 to override any other 'app' modules
    sys.path.insert(0, backend_dir)

from app.main import app
from app.core.database import SessionLocal
from app.modules.users.models import User, UserRole
from app.core.security import get_password_hash

client = TestClient(app)

def get_test_admin():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin_report_test@example.com").first()
        if not admin:
            admin = User(
                email="admin_report_test@example.com",
                hashed_password=get_password_hash("password123"),
                name="Admin Tester",
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
        return admin
    finally:
        db.close()

def get_auth_header():
    admin = get_test_admin()
    response = client.post("/api/auth/login", data={"username": admin.email, "password": "password123"})
    if response.status_code != 200:
        # Fallback if login fails (e.g. if the user exists but password mismatch or something)
        # In a real test environment we'd use a clean DB
        return {}
    token = response.json().get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}

def test_get_dashboard():
    header = get_auth_header()
    response = client.get("/api/reports/dashboard", headers=header)
    assert response.status_code == 200

def test_get_employees():
    header = get_auth_header()
    response = client.get("/api/reports/employees", headers=header)
    assert response.status_code == 200

def test_get_final():
    header = get_auth_header()
    response = client.get("/api/reports/final", headers=header)
    assert response.status_code == 200

def test_export_employees():
    header = get_auth_header()
    response = client.get("/api/reports/export?type=employees", headers=header)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
