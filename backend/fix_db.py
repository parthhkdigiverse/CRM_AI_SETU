import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.core.database import engine
from sqlalchemy import text

def fix_visits_raw():
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE visits SET status = 'OTHER' WHERE status NOT IN ('SATISFIED', 'ACCEPT', 'DECLINE', 'TAKE_TIME_TO_THINK', 'OTHER')"))
        print("Raw DB update executed successfully!")
    except Exception as e:
        print("Error during DB update:", str(e))

if __name__ == "__main__":
    fix_visits_raw()
