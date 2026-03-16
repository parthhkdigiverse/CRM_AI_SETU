import urllib.request
import urllib.parse
import json
import sys

try:
    # 1. Login to get token
    login_url = "http://127.0.0.1:8000/api/auth/login"
    data = urllib.parse.urlencode({'username': 'arjun.mehta@example.com', 'password': 'password123'}).encode('ascii')
    req = urllib.request.Request(login_url, data=data)
    with urllib.request.urlopen(req) as response:
        token_data = json.loads(response.read().decode())
        token = token_data['access_token']

    # 2. Hit the endpoint
    url = "http://127.0.0.1:8000/api/reports/employees?start_date=2026-02-28&end_date=2026-03-30"
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"Success! Found {len(data)} employees.")
        if data:
            print(data[0])
except Exception as e:
    import traceback
    traceback.print_exc()
