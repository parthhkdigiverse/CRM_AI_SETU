from sqlalchemy.engine import make_url
import os
from dotenv import load_dotenv

# Load from backend/.env
env_path = os.path.join("backend", ".env")
load_dotenv(env_path)

db_url = os.getenv("DATABASE_URL")
print(f"Original URL: {db_url}")

if db_url:
    url = make_url(db_url)
    print(f"Parsed Database Name: '{url.database}'")
else:
    print("DATABASE_URL not found in .env")
