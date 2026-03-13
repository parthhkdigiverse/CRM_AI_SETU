
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    print("--- Shops and Owners ---")
    results = conn.execute(text("SELECT id, name, owner_id, status FROM shops")).fetchall()
    for row in results:
        print(f"ID: {row[0]}, Name: {row[1]}, Owner: {row[2]}, Status: {row[3]}")
    
    print("\n--- Visits for Rahul (ID 3) ---")
    results = conn.execute(text("SELECT id, status, visit_date FROM visits WHERE user_id = 3")).fetchall()
    for row in results:
        print(f"ID: {row[0]}, Status: {row[1]}, Date: {row[2]}")
