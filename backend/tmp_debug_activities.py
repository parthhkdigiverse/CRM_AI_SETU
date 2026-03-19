import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.modules.reports.service import ReportService
from app.modules.users.models import User

def debug_activities(user_id):
    db: Session = SessionLocal()
    try:
        print(f"Testing activities for user_id={user_id}...")
        results = ReportService.get_employee_activities(db, user_id=user_id)
        print(f"Success! Found {len(results)} activities.")
        for r in results:
            print(f" - {r}")
    except Exception as e:
        print(f"CRASH detected for user_id={user_id}!!")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_activities(2) # Priya Sharma
