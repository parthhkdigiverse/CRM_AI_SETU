from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from app.core.dependencies import RoleChecker, get_current_active_user
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserRead, UserProfileUpdate
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from pydantic import BaseModel
import uuid
from datetime import date as dt_date
import json

class UserStatusUpdate(BaseModel):
    is_active: bool

class UserRoleUpdate(BaseModel):
    role: UserRole

class UserIncentiveEligibilityUpdate(BaseModel):
    enabled: bool

class RoleIncentiveEligibilityUpdate(BaseModel):
    role: UserRole
    enabled: bool

DEFAULT_ACCESS_POLICY = {
    "page_access": {
        "ADMIN": ["*"],
        "SALES": ["dashboard.html", "timetable.html", "todo.html", "leads.html", "visits.html", "areas.html", "clients.html", "billing.html", "leaves.html", "salary.html", "search.html", "notifications.html", "profile.html", "settings.html", "issues.html", "incentives.html", "employee_report.html", "client_report.html"],
        "TELESALES": ["dashboard.html", "timetable.html", "todo.html", "leads.html", "visits.html", "clients.html", "billing.html", "leaves.html", "salary.html", "search.html", "notifications.html", "profile.html", "settings.html", "issues.html", "incentives.html", "employee_report.html", "client_report.html"],
        "PROJECT_MANAGER": ["dashboard.html", "timetable.html", "todo.html", "projects.html", "projects_demo.html", "meetings.html", "issues.html", "clients.html", "billing.html", "feedback.html", "reports.html", "leaves.html", "salary.html", "search.html", "notifications.html", "profile.html", "settings.html", "incentives.html", "employee_report.html", "client_report.html"],
        "PROJECT_MANAGER_AND_SALES": ["dashboard.html", "timetable.html", "todo.html", "leads.html", "visits.html", "areas.html", "projects.html", "projects_demo.html", "meetings.html", "issues.html", "clients.html", "billing.html", "feedback.html", "reports.html", "leaves.html", "salary.html", "search.html", "notifications.html", "profile.html", "settings.html", "incentives.html", "employee_report.html", "client_report.html"],
        "CLIENT": ["dashboard.html"]
    },
    "feature_access": {
        "issue_create_roles": ["ADMIN", "SALES", "TELESALES", "PROJECT_MANAGER", "PROJECT_MANAGER_AND_SALES"],
        "issue_manage_roles": ["ADMIN", "PROJECT_MANAGER", "PROJECT_MANAGER_AND_SALES", "SALES", "TELESALES"],
        "invoice_creator_roles": ["ADMIN", "SALES", "TELESALES", "PROJECT_MANAGER_AND_SALES"],
        "invoice_verifier_roles": ["ADMIN"],
        "leave_apply_roles": ["SALES", "TELESALES", "PROJECT_MANAGER", "PROJECT_MANAGER_AND_SALES"],
        "leave_edit_own_roles": ["SALES", "TELESALES", "PROJECT_MANAGER", "PROJECT_MANAGER_AND_SALES"],
        "leave_cancel_own_roles": ["SALES", "TELESALES", "PROJECT_MANAGER", "PROJECT_MANAGER_AND_SALES"],
        "leave_manage_roles": ["ADMIN"],
        "salary_manage_roles": ["ADMIN"],
        "salary_view_all_roles": ["ADMIN"],
        "incentive_manage_roles": ["ADMIN"],
        "incentive_view_all_roles": ["ADMIN"],
        "employee_manage_roles": ["ADMIN"]
    }
}

def _normalize_role_list(roles: Any, fallback: list) -> list:
    valid_roles = {r.value for r in UserRole}
    if not isinstance(roles, list):
        roles = fallback
    normalized = []
    for role in roles:
        role_name = str(role).upper().strip()
        if role_name in valid_roles and role_name not in normalized:
            normalized.append(role_name)
    return normalized or fallback

async def _load_access_policy() -> dict:
    from app.modules.salary.models import AppSetting
    row = await AppSetting.find_one(AppSetting.key == "ui_access_policy")
    if not row or not row.value:
        return DEFAULT_ACCESS_POLICY
    try:
        data = json.loads(row.value)
        if not isinstance(data, dict):
            return DEFAULT_ACCESS_POLICY
        page_access = data.get("page_access") or {}
        feature_access = data.get("feature_access") or {}
        merged_page_access = {}
        for role, pages in DEFAULT_ACCESS_POLICY["page_access"].items():
            custom_pages = page_access.get(role)
            if isinstance(custom_pages, list) and custom_pages:
                merged_page_access[role] = [str(p).strip() for p in custom_pages if str(p).strip()]
            else:
                merged_page_access[role] = pages
        merged_feature_access = {}
        for key, roles in DEFAULT_ACCESS_POLICY["feature_access"].items():
            merged_feature_access[key] = _normalize_role_list(feature_access.get(key), roles)
        if "ADMIN" not in merged_feature_access["invoice_verifier_roles"]:
            merged_feature_access["invoice_verifier_roles"].append("ADMIN")
        if "ADMIN" not in merged_feature_access["invoice_creator_roles"]:
            merged_feature_access["invoice_creator_roles"].append("ADMIN")
        return {"page_access": merged_page_access, "feature_access": merged_feature_access}
    except Exception:
        return DEFAULT_ACCESS_POLICY

async def _save_access_policy(policy: dict) -> None:
    from app.modules.salary.models import AppSetting
    row = await AppSetting.find_one(AppSetting.key == "ui_access_policy")
    payload = json.dumps(policy)
    if row:
        row.value = payload
        await row.save()
    else:
        await AppSetting(key="ui_access_policy", value=payload).insert()

async def _sync_billing_role_settings(policy: dict) -> None:
    from app.modules.salary.models import AppSetting
    feature_access = policy.get("feature_access") or {}
    creator_roles = feature_access.get("invoice_creator_roles") or ["ADMIN", "SALES", "TELESALES", "PROJECT_MANAGER_AND_SALES"]
    verifier_roles = feature_access.get("invoice_verifier_roles") or ["ADMIN"]
    for key, roles in [("invoice_creator_roles", creator_roles), ("invoice_verifier_roles", verifier_roles)]:
        row = await AppSetting.find_one(AppSetting.key == key)
        value = ",".join(sorted({str(r).upper() for r in roles if str(r).strip()}))
        if not value:
            value = "ADMIN"
        if row:
            row.value = value
            await row.save()
        else:
            await AppSetting(key=key, value=value).insert()

router = APIRouter()
admin_checker = RoleChecker([UserRole.ADMIN])

@router.get("/access-policy")
async def get_access_policy(current_user: User = Depends(admin_checker)) -> Any:
    return await _load_access_policy()

@router.put("/access-policy")
async def update_access_policy(payload: dict, current_user: User = Depends(admin_checker)) -> Any:
    page_access = payload.get("page_access")
    feature_access = payload.get("feature_access")
    if not isinstance(page_access, dict) or not isinstance(feature_access, dict):
        raise HTTPException(status_code=400, detail="page_access and feature_access are required")
    normalized_page_access = {}
    valid_roles = {r.value for r in UserRole}
    for role, pages in page_access.items():
        role_name = str(role).upper()
        if role_name not in valid_roles:
            continue
        if not isinstance(pages, list):
            continue
        normalized_page_access[role_name] = [str(p).strip() for p in pages if str(p).strip()]
    normalized_feature_access = {
        key: _normalize_role_list(feature_access.get(key), roles)
        for key, roles in DEFAULT_ACCESS_POLICY["feature_access"].items()
    }
    if "ADMIN" not in normalized_feature_access["invoice_verifier_roles"]:
        normalized_feature_access["invoice_verifier_roles"].append("ADMIN")
    if "ADMIN" not in normalized_feature_access["invoice_creator_roles"]:
        normalized_feature_access["invoice_creator_roles"].append("ADMIN")
    new_policy = {
        "page_access": normalized_page_access or DEFAULT_ACCESS_POLICY["page_access"],
        "feature_access": normalized_feature_access,
    }
    await _save_access_policy(new_policy)
    await _sync_billing_role_settings(new_policy)
    return new_policy

@router.get("/access-policy/effective")
async def get_effective_access_policy(current_user: User = Depends(get_current_active_user)) -> Any:
    policy = await _load_access_policy()
    role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    allowed_pages = (policy.get("page_access") or {}).get(role, [])
    if role == "ADMIN" and "*" not in allowed_pages:
        allowed_pages = ["*"]
    return {"role": role, "allowed_pages": allowed_pages, "feature_access": policy.get("feature_access") or {}, "policy": policy}

@router.get("/", response_model=List[UserRead])
async def list_users(current_user: User = Depends(get_current_active_user)) -> Any:
    if current_user.role != UserRole.ADMIN:
        return [current_user]
    return await User.find(User.is_deleted != True).to_list()

@router.get("/project-managers", response_model=List[UserRead])
async def list_project_managers(current_user: User = Depends(get_current_active_user)) -> Any:
    pm_roles = [UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES, UserRole.ADMIN]
    return await User.find(User.is_deleted != True, User.role.in_(pm_roles)).to_list()

@router.patch("/incentive-eligibility/by-role")
async def update_role_incentive_eligibility(payload: RoleIncentiveEligibilityUpdate, current_user: User = Depends(admin_checker)) -> Any:
    if payload.role == UserRole.CLIENT:
        raise HTTPException(status_code=400, detail="CLIENT role cannot receive incentives")
    users = await User.find(User.is_deleted != True, User.role == payload.role).to_list()
    for user in users:
        user.incentive_enabled = payload.enabled
        await user.save()
    return {"updated": len(users), "role": payload.role, "incentive_enabled": payload.enabled}

@router.patch("/{user_id}/incentive-eligibility", response_model=UserRead)
async def update_user_incentive_eligibility(user_id: str, payload: UserIncentiveEligibilityUpdate, current_user: User = Depends(admin_checker)) -> Any:
    user = await User.find_one(User.id == user_id, User.is_deleted != True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.CLIENT:
        raise HTTPException(status_code=400, detail="CLIENT role cannot receive incentives")
    user.incentive_enabled = payload.enabled
    await user.save()
    return user

@router.patch("/{user_id}/role", response_model=UserRead)
async def update_user_role(user_id: str, role_in: UserRoleUpdate, request: Request, current_user: User = Depends(admin_checker)) -> Any:
    user = await User.find_one(User.id == user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    old_role = user.role
    user.role = role_in.role
    await user.save()
    activity_logger = ActivityLogger()
    await activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.UPDATE, entity_type=EntityType.USER, entity_id=user.id, old_data={"role": old_role}, new_data={"role": user.role}, request=request)
    return user

@router.patch("/{user_id}/status", response_model=UserRead)
async def update_user_status(user_id: str, status_in: UserStatusUpdate, request: Request, current_user: User = Depends(admin_checker)) -> Any:
    user = await User.find_one(User.id == user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    old_status = user.is_active
    user.is_active = status_in.is_active
    await user.save()
    activity_logger = ActivityLogger()
    await activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.UPDATE, entity_type=EntityType.USER, entity_id=user.id, old_data={"is_active": old_status}, new_data={"is_active": user.is_active}, request=request)
    return user

@router.get("/config/employee-code")
async def get_employee_code_settings(current_user: User = Depends(admin_checker)) -> Any:
    from app.modules.users.service import UserService
    return await UserService().get_employee_code_settings()

@router.put("/config/employee-code")
async def update_employee_code_settings(payload: dict, current_user: User = Depends(admin_checker)) -> Any:
    from app.modules.users.service import UserService
    enabled = payload.get("enabled", True)
    prefix = payload.get("prefix")
    next_seq = payload.get("next_seq")
    if prefix is None or next_seq is None:
        raise HTTPException(status_code=400, detail="prefix and next_seq are required")
    try:
        next_seq = int(next_seq)
    except ValueError:
        raise HTTPException(status_code=400, detail="next_seq must be an integer")
    return await UserService().update_employee_code_settings(enabled, prefix, next_seq)

@router.patch("/{user_id}/profile", response_model=UserRead)
async def admin_update_user_profile(user_id: str, profile_in: UserProfileUpdate, request: Request, current_user: User = Depends(admin_checker)) -> Any:
    user = await User.find_one(User.id == user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    old_name = user.name
    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    await user.save()
    activity_logger = ActivityLogger()
    await activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.UPDATE, entity_type=EntityType.USER, entity_id=user.id, old_data={"name": old_name}, new_data={"name": user.name}, request=request)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, request: Request, current_user: User = Depends(admin_checker)):
    user = await User.find_one(User.id == user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    old_deleted_status = user.is_deleted
    user.is_deleted = True
    await user.save()
    activity_logger = ActivityLogger()
    await activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.DELETE, entity_type=EntityType.USER, entity_id=user_id, old_data={"is_deleted": old_deleted_status}, new_data={"is_deleted": True}, request=request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/batch-delete")
async def batch_delete_users(ids: List[int], request: Request, current_user: User = Depends(admin_checker)):
    users = await User.find(User.id.in_(ids)).to_list()
    for user in users:
        user.is_deleted = True
        await user.save()
    activity_logger = ActivityLogger()
    await activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.DELETE, entity_type=EntityType.USER, entity_id=0, old_data={"batch_ids": ids}, new_data={"is_deleted": True}, request=request)
    return {"message": f"Successfully deleted {len(ids)} users"}

@router.post("/{user_id}/referral-code")
async def generate_referral_code(user_id: str, current_user: User = Depends(get_current_active_user)) -> Any:
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    user = await User.find_one(User.id == user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    allowed_roles = [UserRole.SALES, UserRole.TELESALES, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES, UserRole.ADMIN]
    if user.role not in allowed_roles:
        raise HTTPException(status_code=400, detail="Referral codes can only be generated for SALES, TELESALES, or PROJECT MANAGER roles")
    if user.referral_code:
        return {"user_id": user.id, "code": user.referral_code}
    code = f"REF-{user.id}-{str(uuid.uuid4())[:8].upper()}"
    existing = await User.find_one(User.referral_code == code, User.id != user.id)
    if existing:
        raise HTTPException(status_code=400, detail="Referral code collision; try again")
    user.referral_code = code
    await user.save()
    return {"user_id": user.id, "code": user.referral_code}

@router.get("/{user_id}/referral-code")
async def get_referral_code(user_id: str, current_user: User = Depends(admin_checker)) -> Any:
    user = await User.find_one(User.id == user_id)
    if not user or not user.referral_code:
        raise HTTPException(status_code=404, detail="Referral code not set for this user")
    return {"user_id": user.id, "code": user.referral_code}

@router.get("/{pm_id}/availability")
async def get_pm_availability(pm_id: str, date: dt_date, current_user: User = Depends(get_current_active_user)) -> Any:
    from app.modules.meetings.models import MeetingSummary
    from app.modules.clients.models import Client
    pm = await User.find_one(User.id == pm_id, User.role.in_([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]))
    if not pm:
        raise HTTPException(status_code=404, detail="Project Manager not found")
    clients = await Client.find(Client.pm_id == pm_id).to_list()
    client_ids = [c.id for c in clients]
    meetings = await MeetingSummary.find(MeetingSummary.client_id.in_(client_ids), MeetingSummary.status != "CANCELLED").to_list()
    meetings = [m for m in meetings if m.date and m.date.date() == date]
    booked_hours = [m.date.hour for m in meetings]
    free_slots = [f"{h:02d}:00" for h in range(9, 18) if h not in booked_hours]
    return {"pm_id": pm_id, "date": date, "free_slots": free_slots}

@router.get("/public/lookup/{referral_code}")
async def lookup_user_by_referral(referral_code: str) -> Any:
    user = await User.find_one(User.referral_code == referral_code)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    role_str = role_str.replace("_", " ").title()
    return {"name": user.name, "referral_code": user.referral_code, "role": role_str}
