import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from dotenv import load_dotenv

# Add backend to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")
sys.path.append(backend_dir)

load_dotenv(os.path.join(backend_dir, ".env"))

db_url = os.getenv("DATABASE_URL")
print(f"Testing with make_url and DATABASE_URL: {db_url}")

try:
    url = make_url(db_url)
    print(f"Parsed URL database: {url.database}")
    engine = create_engine(url)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("Connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")
