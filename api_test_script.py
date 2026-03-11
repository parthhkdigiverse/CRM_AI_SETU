import requests
import json
import base64

BASE_URL = "http://127.0.0.1:8000/api"

def test_feedback_endpoints():
    print("Testing Feedback Endpoints...")
    
    # 1. Test Public Submit (No Auth)
    payload = {
        "rating": 5,
        "comments": "Test from script",
        "client_name": "Test Client",
        "mobile": "1234567890",
        "shop_name": "Test Shop",
        "product": "Test Product",
        "agent_name": "Test Agent",
        "referral_code": "REF-TEST"
    }
    
    try:
        r = requests.post(f"{BASE_URL}/feedback/public/submit", json=payload)
        print(f"POST /feedback/public/submit: {r.status_code}")
        if r.status_code not in [201, 200]:
            print(f"Error Body: {r.text}")
        
        # 2. Test Admin All (Needs Auth) - Expecting 401
        r = requests.get(f"{BASE_URL}/feedback/all")
        print(f"GET /feedback/all: {r.status_code}")
        
        # 3. Test Referral Lookup
        r = requests.get(f"{BASE_URL}/users/public/lookup/REF-TEST")
        print(f"GET /users/public/lookup/REF-TEST: {r.status_code}")
        if r.status_code != 404:
             print(f"Referral Body: {r.text}")

    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_feedback_endpoints()
