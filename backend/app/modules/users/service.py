from app.modules.users.models import User
import string
import random

class UserService:
    async def generate_referral_code(self, user_id: str):
        user = await User.find_one(User.id == user_id)
        if not user:
            return None
        if user.referral_code:
            return user.referral_code
        prefix = "SETU"
        role_part = user.role[:3].upper()
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        code = f"{prefix}-{role_part}-{random_part}"
        while await User.find_one(User.referral_code == code):
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            code = f"{prefix}-{role_part}-{random_part}"
        user.referral_code = code
        await user.save()
        return code

    async def get_user_by_referral(self, code: str):
        return await User.find_one(User.referral_code == code)

    async def get_next_employee_code(self):
        from app.modules.salary.models import AppSetting
        prefix_row = await AppSetting.find_one(AppSetting.key == "emp_code_prefix")
        seq_row = await AppSetting.find_one(AppSetting.key == "emp_code_next_seq")
        enabled_row = await AppSetting.find_one(AppSetting.key == "emp_code_enabled")
        enabled = enabled_row.value.lower() == "true" if enabled_row else True
        if not enabled:
            return None, None
        prefix = prefix_row.value if prefix_row else "EMP"
        seq = int(seq_row.value) if seq_row else 1
        code = f"{prefix}{seq:03d}"
        while await User.find_one(User.employee_code == code):
            seq += 1
            code = f"{prefix}{seq:03d}"
        return code, seq

    async def increment_employee_code_seq(self, current_seq: int):
        from app.modules.salary.models import AppSetting
        seq_row = await AppSetting.find_one(AppSetting.key == "emp_code_next_seq")
        if seq_row:
            seq_row.value = str(current_seq + 1)
            await seq_row.save()
        else:
            await AppSetting(key="emp_code_next_seq", value=str(current_seq + 1)).insert()

    async def get_employee_code_settings(self):
        from app.modules.salary.models import AppSetting
        prefix_row = await AppSetting.find_one(AppSetting.key == "emp_code_prefix")
        seq_row = await AppSetting.find_one(AppSetting.key == "emp_code_next_seq")
        enabled_row = await AppSetting.find_one(AppSetting.key == "emp_code_enabled")
        return {
            "enabled": enabled_row.value.lower() == "true" if enabled_row else True,
            "prefix": prefix_row.value if prefix_row else "EMP",
            "next_seq": int(seq_row.value) if seq_row else 1
        }

    async def update_employee_code_settings(self, enabled: bool, prefix: str, next_seq: int):
        from app.modules.salary.models import AppSetting
        settings = [
            ("emp_code_enabled", str(enabled).lower()),
            ("emp_code_prefix", prefix),
            ("emp_code_next_seq", str(next_seq))
        ]
        for key, val in settings:
            row = await AppSetting.find_one(AppSetting.key == key)
            if row:
                row.value = val
                await row.save()
            else:
                await AppSetting(key=key, value=val).insert()
        return {"enabled": enabled, "prefix": prefix, "next_seq": next_seq}
