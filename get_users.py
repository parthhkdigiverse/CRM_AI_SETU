import sys
import os
sys.path.append('e:/CRM AI SETU/backend')
from app.database import SessionLocal
from app.models.user import User

db = SessionLocal()
users = db.query(User).all()
for u in users:
    print(f"{u.id} | {u.email} | {u.role.name}")
