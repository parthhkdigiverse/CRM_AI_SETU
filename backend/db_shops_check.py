
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    print("--- Shops Summary ---")
    results = conn.execute(text("SELECT status, count(*) FROM shops GROUP BY status")).fetchall()
    for row in results:
        print(f"Status: {row[0]}, Count: {row[1]}")
    
    print("\n--- Shops for Rahul (ID: 3) ---")
    results = conn.execute(text("SELECT status, count(*) FROM shops WHERE owner_id = 3 GROUP BY status")).fetchall()
    for row in results:
        print(f"Status: {row[0]}, Count: {row[1]}")

    print("\n--- Shops for Priya (ID: 2) ---")
    results = conn.execute(text("SELECT status, count(*) FROM shops WHERE owner_id = 2 GROUP BY status")).fetchall()
    for row in results:
        print(f"Status: {row[0]}, Count: {row[1]}")
