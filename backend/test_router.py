from app.core.database import SessionLocal
from app.modules.timetable.router import get_timetable
from app.modules.users.models import User
import datetime

db = SessionLocal()
try:
    user = db.query(User).filter(User.email == 'admin@example.com').first()
    start = datetime.datetime.now() - datetime.timedelta(days=30)
    end = datetime.datetime.now() + datetime.timedelta(days=30)
    res = get_timetable(start, end, db, user)
    print('Success')
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
