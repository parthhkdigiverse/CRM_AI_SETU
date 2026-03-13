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

    def get_next_employee_code(self):
        """Generate the next sequential employee code based on settings."""
        from app.modules.salary.models import AppSetting
        
        prefix_row = self.db.query(AppSetting).filter(AppSetting.key == "emp_code_prefix").first()
        seq_row = self.db.query(AppSetting).filter(AppSetting.key == "emp_code_next_seq").first()
        enabled_row = self.db.query(AppSetting).filter(AppSetting.key == "emp_code_enabled").first()
        
        enabled = enabled_row.value.lower() == "true" if enabled_row else True
        if not enabled:
            return None, None

        prefix = prefix_row.value if prefix_row else "EMP"
        seq = int(seq_row.value) if seq_row else 1
        
        # Format: PREFIX + 3-digit padded number (e.g., EMP001)
        # If user wants different padding, we can adjust, but 3 is a common default.
        code = f"{prefix}{seq:03d}"
        
        # Ensure uniqueness by checking DB and incrementing if exists
        while self.db.query(User).filter(User.employee_code == code).first():
            seq += 1
            code = f"{prefix}{seq:03d}"
            
        return code, seq

    def increment_employee_code_seq(self, current_seq: int):
        """Increment the sequence in settings."""
        from app.modules.salary.models import AppSetting
        seq_row = self.db.query(AppSetting).filter(AppSetting.key == "emp_code_next_seq").first()
        if seq_row:
            seq_row.value = str(current_seq + 1)
        else:
            self.db.add(AppSetting(key="emp_code_next_seq", value=str(current_seq + 1)))
        self.db.commit()

    def get_employee_code_settings(self):
        """Fetch current employee code settings."""
        from app.modules.salary.models import AppSetting
        prefix_row = self.db.query(AppSetting).filter(AppSetting.key == "emp_code_prefix").first()
        seq_row = self.db.query(AppSetting).filter(AppSetting.key == "emp_code_next_seq").first()
        enabled_row = self.db.query(AppSetting).filter(AppSetting.key == "emp_code_enabled").first()
        
        return {
            "enabled": enabled_row.value.lower() == "true" if enabled_row else True,
            "prefix": prefix_row.value if prefix_row else "EMP",
            "next_seq": int(seq_row.value) if seq_row else 1
        }

    def update_employee_code_settings(self, enabled: bool, prefix: str, next_seq: int):
        """Update employee code settings."""
        from app.modules.salary.models import AppSetting
        
        settings = [
            ("emp_code_enabled", str(enabled).lower()),
            ("emp_code_prefix", prefix),
            ("emp_code_next_seq", str(next_seq))
        ]
        
        for key, val in settings:
            row = self.db.query(AppSetting).filter(AppSetting.key == key).first()
            if row:
                row.value = val
            else:
                self.db.add(AppSetting(key=key, value=val))
        self.db.commit()
        return {"enabled": enabled, "prefix": prefix, "next_seq": next_seq}
