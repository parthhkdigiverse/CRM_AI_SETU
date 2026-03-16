from app.core.database import SessionLocal
from app.modules.reports.service import ReportService
from app.modules.users.models import User
import traceback
import json

db = SessionLocal()
try:
    res = ReportService.get_employee_activities(db, user_id=2, start_date="2026-02-28", end_date="2026-03-30")
    print("Success. Total:", len(res))
    if res:
        print(res[0])
except Exception as e:
    traceback.print_exc()
finally:
    db.close()
