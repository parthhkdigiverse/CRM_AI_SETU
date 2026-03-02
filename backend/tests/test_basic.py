import sys
import os

# Crucial: Add 'backend' to the very front of sys.path to prioritize 
# 'backend/app' over 'e:/CRM AI SETU/app.py'
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, backend_dir)

import pytest
from fastapi.testclient import TestClient
from app.main import app




client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_config_endpoint():
    response = client.get("/api/config")
    assert response.status_code == 200
    assert "API_BASE_URL" in response.json()
