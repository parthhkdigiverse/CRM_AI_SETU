import sys
sys.path.append('.')
from sqlalchemy import text
from app.core.database import SessionLocal
db = SessionLocal()
res = db.execute(text("UPDATE bills SET invoice_number = invoice_number || '-del-' || id WHERE is_deleted = TRUE AND invoice_number NOT LIKE '%-del-%';"))
db.commit()
print('Rows affected:', res.rowcount)
