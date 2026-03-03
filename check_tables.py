import os
import sys
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

# Add backend to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")
sys.path.append(backend_dir)

load_dotenv(os.path.join(backend_dir, ".env"))

db_url = os.getenv("DATABASE_URL")
print(f"Checking tables for: {db_url}")

try:
    engine = create_engine(db_url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables: {tables}")
    if not tables:
        print("No tables found. Migrations need to be run.")
except Exception as e:
    print(f"Check failed: {e}")
