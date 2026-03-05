import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add backend to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")
sys.path.append(backend_dir)

load_dotenv(os.path.join(backend_dir, ".env"))

db_url = os.getenv("DATABASE_URL")
print(f"Checking users for: {db_url}")

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT email, role FROM users LIMIT 10"))
        users = result.fetchall()
        print(f"Users found: {len(users)}")
        for user in users:
            print(f"- {user.email} ({user.role})")
except Exception as e:
    print(f"Check failed: {e}")
