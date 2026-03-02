import sys
import os

# Ensure project root and backend are in path
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal, engine
from app.modules.users.models import User, UserRole
from app.core.security import get_password_hash
from sqlalchemy import text

def reset_admin():
    print("Testing database connection...")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection successful.")
    except Exception as e:
        print(f"DATABASE CONNECTION FAILED: {e}")
        return

    db = SessionLocal()
    try:
        email = "admin@example.com"
        password = "password123"
        print(f"Target Account: {email}")
        
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            print(f"User found (ID: {user.id}). Updating password and ensuring admin role...")
            user.hashed_password = get_password_hash(password)
            user.role = UserRole.ADMIN
            user.is_active = True
        else:
            print(f"User not found. Creating new admin account...")
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                role=UserRole.ADMIN,
                is_active=True,
                name="System Administrator"
            )
            db.add(user)
        
        db.commit()
        print("Success: Admin account is ready.")
        print(f"Username: {email}")
        print(f"Password: {password}")
        
    except Exception as e:
        print(f"ERROR DURING RESET: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin()
