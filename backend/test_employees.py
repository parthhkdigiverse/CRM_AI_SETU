from app.core.database import SessionLocal
from app.modules.reports.service import ReportService
from app.modules.users.models import User
import traceback
import json

db = SessionLocal()
try:
    admin = db.query(User).filter(User.role == "ADMIN").first()
    res = ReportService.get_employee_performance(db, requesting_user=admin, start_date="2026-02-28", end_date="2026-03-30")
    print("Success. Total:", len(res))
    if res:
        print(json.dumps(res[0], indent=2))
except Exception as e:
    traceback.print_exc()
finally:
    db.close()
