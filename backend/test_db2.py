import sys
sys.path.append('.')
from sqlalchemy import text
from app.core.database import SessionLocal
db = SessionLocal()
res = db.execute(text("SELECT id, invoice_number, is_deleted FROM bills WHERE invoice_number LIKE '%001%';")).fetchall()
for r in res:
    print(r)
