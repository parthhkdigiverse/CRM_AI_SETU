
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    print("--- ALL SHOPS ---")
    results = conn.execute(text("SELECT id, name, owner_id, status FROM shops")).fetchall()
    for row in results:
        owner = row[2] if row[2] is not None else "None"
        print(f"Shop ID: {row[0]}, Name: {row[1]}, Owner ID: {owner}, Status: {row[3]}")
    
    print("\n--- ALL USERS ---")
    results = conn.execute(text("SELECT id, name FROM users")).fetchall()
    for row in results:
        print(f"User ID: {row[0]}, Name: {row[1]}")
