import urllib.request
import json
try:
    url = "http://127.0.0.1:8000/api/reports/employees?start_date=2026-02-28&end_date=2026-03-30"
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer test'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"Success! Found {len(data)} employees.")
        if data:
            print(data[0])
except Exception as e:
    import traceback
    traceback.print_exc()
