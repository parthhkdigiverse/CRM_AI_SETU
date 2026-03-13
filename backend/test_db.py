import sys
sys.path.append('.')
from sqlalchemy import text
from app.core.database import SessionLocal
db = SessionLocal()
res = db.execute(text('SELECT id, invoice_number, is_deleted, status FROM bills ORDER BY id DESC LIMIT 10;')).fetchall()
for r in res:
    print(r)
