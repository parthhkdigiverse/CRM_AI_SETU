import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# Add backend to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")
sys.path.append(backend_dir)

load_dotenv(os.path.join(backend_dir, ".env"))

from app.core.config import settings
from app.modules.users.models import User

print(f"Testing query with DATABASE_URL: {settings.DATABASE_URL}")

try:
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    print("Attempting to query User...")
    user = db.query(User).filter(User.email == "test@example.com").first()
    print(f"Query successful. User: {user}")
    
except Exception as e:
    print(f"Query FAILED with {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
finally:
    if 'db' in locals():
        db.close()
