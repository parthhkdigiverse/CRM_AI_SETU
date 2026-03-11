from sqlalchemy.orm import Session
from app.modules.users.models import User
import uuid
import string
import random

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def generate_referral_code(self, user_id: int):
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        if user.referral_code:
            return user.referral_code
        
        # Generate a unique referral code: SETU-ROLE-RANDOM
        prefix = "SETU"
        role_part = user.role[:3].upper()
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        
        code = f"{prefix}-{role_part}-{random_part}"
        
        # Ensure uniqueness
        while self.db.query(User).filter(User.referral_code == code).first():
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            code = f"{prefix}-{role_part}-{random_part}"
            
        user.referral_code = code
        self.db.commit()
        self.db.refresh(user)
        return code

    def get_user_by_referral(self, code: str):
        return self.db.query(User).filter(User.referral_code == code).first()
