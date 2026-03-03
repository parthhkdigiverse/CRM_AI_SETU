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
print(f"Attempting to connect to: {db_url}")

try:
    engine = create_engine(db_url)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("Connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")
