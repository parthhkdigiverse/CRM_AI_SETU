from app.modules.activity_logs.models import ActivityLog, ActionType, EntityType
from app.modules.users.models import UserRole
from fastapi import Request
from datetime import datetime

class ActivityLogger:
    def __init__(self):
        self.sensitive_fields = {"password", "hashed_password", "token", "access_token", "refresh_token", "secret", "otp"}

    def _filter_sensitive_data(self, data: dict):
        if not data:
            return None
        return {k: (v if k not in self.sensitive_fields else "[REDACTED]") for k, v in data.items()}

    async def log_activity(
        self,
        user_id,
        user_role: UserRole,
        action: ActionType,
        entity_type: EntityType,
        entity_id,
        old_data: dict = None,
        new_data: dict = None,
        request: Request = None
    ):
        ip_address = request.client.host if request else None
        role_str = user_role.value if hasattr(user_role, "value") else str(user_role)

        activity_log = ActivityLog(
            user_id=str(user_id),
            user_role=role_str,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            old_data=self._filter_sensitive_data(old_data),
            new_data=self._filter_sensitive_data(new_data),
            ip_address=ip_address,
            created_at=datetime.utcnow()
        )
        await activity_log.insert()
        return activity_log

    async def get_logs(self, skip: int = 0, limit: int = 100):
        try:
            from app.modules.users.models import User
            logs = await ActivityLog.find_all().sort(-ActivityLog.created_at).skip(skip).limit(limit).to_list()
            for log in logs:
                user = await User.find_one(User.id == log.user_id)
                if user:
                    log.user_name = user.name or user.email or f"User #{log.user_id}"
                else:
                    log.user_name = "System"
            return logs
        except Exception as e:
            print(f"Error fetching logs: {e}")
            return []
