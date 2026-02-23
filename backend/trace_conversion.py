import requests
import json
import traceback
import time

BASE_URL = "http://127.0.0.1:8123/api"

# Register SALES user
email = f"sales_{int(time.time())}@test.com"
r = requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": "Password123!", "role": "SALES", "is_active": True})
login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": "Password123!"})
sales_token = login_res.json()["access_token"]
sales_h = {"Authorization": f"Bearer {sales_token}", "Content-Type": "application/json"}

try:
    lead_res = requests.post(f"{BASE_URL}/leads/", headers=sales_h, json={"name": "Trace Convert Lead", "phone": "999"})
    if lead_res.status_code != 201:
        print("Failed to create lead:", lead_res.text)
        exit(1)
        
    lead = lead_res.json()
    conv_res = requests.post(f"{BASE_URL}/leads/{lead['id']}/convert", headers=sales_h)
    print("Convert status:", conv_res.status_code)
    print("Convert output:", conv_res.text)
except Exception as e:
    traceback.print_exc()
