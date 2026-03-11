import sys
sys.path.insert(0, 'e:/CRM AI SETU/backend')
from sqlalchemy import text, inspect
from app.core.database import engine

inspector = inspect(engine)

print("=== salary_slips columns ===")
for col in inspector.get_columns('salary_slips'):
    print(f"  {col['name']} ({col['type']})")

print("\n=== leave_records columns ===")
for col in inspector.get_columns('leave_records'):
    print(f"  {col['name']} ({col['type']})")
