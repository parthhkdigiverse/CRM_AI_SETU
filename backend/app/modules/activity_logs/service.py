from sqlalchemy.orm import Session
from app.modules.activity_logs.models import ActivityLog, ActionType, EntityType
from app.modules.users.models import UserRole
from app.modules.activity_logs.schemas import ActivityLogCreate
from fastapi import Request

class ActivityLogger:
    def __init__(self, db: Session):
        self.db = db
        self.sensitive_fields = {"password", "hashed_password", "token", "access_token", "refresh_token", "secret", "otp"}

    def _filter_sensitive_data(self, data: dict):
        if not data:
            return None
        return {k: (v if k not in self.sensitive_fields else "[REDACTED]") for k, v in data.items()}

    async def log_activity(
        self,
        user_id: int,
        user_role: UserRole, # Expecting enum here, but model stores string
        action: ActionType,
        entity_type: EntityType,
        entity_id: int,
        old_data: dict = None,
        new_data: dict = None,
        request: Request = None
    ):
        ip_address = request.client.host if request else None
        
        # Ensure user_role is string
        role_str = user_role.value if hasattr(user_role, 'value') else str(user_role)

        activity_log = ActivityLog(
            user_id=user_id,
            user_role=role_str,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_data=self._filter_sensitive_data(old_data),
            new_data=self._filter_sensitive_data(new_data),
            ip_address=ip_address
        )
        self.db.add(activity_log)
        self.db.commit()
        self.db.refresh(activity_log)
        return activity_log

    def get_logs(self, skip: int = 0, limit: int = 100):
        return self.db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).offset(skip).limit(limit).all()
