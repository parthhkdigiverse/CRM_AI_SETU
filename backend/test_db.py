
from app.core.database import SessionLocal
from app.modules.users.models import User

try:
    db = SessionLocal()
    user3 = db.query(User).filter(User.id == 3).first()
    print(f'User 3 before: {user3.name}')
    user3.name = 'Test Direct Update'
    db.commit()
    db.refresh(user3)
    print(f'User 3 after: {user3.name}')
except Exception as e:
    print(f'Error: {e}')

