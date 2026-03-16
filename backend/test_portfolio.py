from app.core.database import SessionLocal
from app.modules.reports.service import ReportService
from app.modules.users.models import User
import traceback

db = SessionLocal()
try:
    admin = db.query(User).filter(User.role == "ADMIN").first()
    res = ReportService.get_project_portfolio(db, requesting_user=admin)
    print("Success. Total:", len(res))
    if res:
        print(res[0])
except Exception as e:
    traceback.print_exc()
finally:
    db.close()
