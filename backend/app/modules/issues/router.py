from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, BackgroundTasks, Request
import json
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.clients.models import Client
from app.modules.issues.models import Issue
from app.modules.issues.schemas import IssueCreate, IssueRead, IssueUpdate
from app.modules.issues.service import IssueService
from datetime import datetime, timezone

router = APIRouter()
global_router = APIRouter()

admin_checker = RoleChecker([UserRole.ADMIN])
staff_checker = RoleChecker([UserRole.ADMIN, UserRole.SALES, UserRole.TELESALES, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])

DEFAULT_FEATURE_ACCESS = {
    "issue_create_roles": ["ADMIN", "SALES", "TELESALES", "PROJECT_MANAGER", "PROJECT_MANAGER_AND_SALES"],
    "issue_manage_roles": ["ADMIN", "PROJECT_MANAGER", "PROJECT_MANAGER_AND_SALES", "SALES", "TELESALES"],
}

def _current_role_name(current_user: User) -> str:
    return current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)

async def _get_feature_roles(feature_key: str) -> set:
    from app.modules.salary.models import AppSetting
    fallback = set(DEFAULT_FEATURE_ACCESS.get(feature_key, ["ADMIN"]))
    row = await AppSetting.find_one(AppSetting.key == "ui_access_policy")
    if not row or not row.value:
        return fallback
    try:
        data = json.loads(row.value)
        feature_access = data.get("feature_access") or {}
        configured = feature_access.get(feature_key)
        if isinstance(configured, list) and configured:
            return {str(r).upper() for r in configured if str(r).strip()}
    except Exception:
        return fallback
    return fallback

async def _require_feature_access(current_user: User, feature_key: str, detail: str = "Access denied") -> None:
    role_name = _current_role_name(current_user).upper()
    if role_name not in await _get_feature_roles(feature_key):
        raise HTTPException(status_code=403, detail=detail)

@global_router.get("/", response_model=List[IssueRead])
async def read_global_issues(skip: int = 0, limit: int = 100, status: Optional[str] = None, severity: Optional[str] = None, client_id: Optional[str] = None, assigned_to_id: Optional[int] = None, pm_id: Optional[str] = None, current_user: User = Depends(staff_checker)) -> Any:
    service = IssueService()
    if assigned_to_id is None and pm_id and pm_id not in {"ALL", "all"}:
        try:
            assigned_to_id = int(pm_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid pm_id")
    return await service.get_all_issues_for_user(current_user=current_user, skip=skip, limit=limit, status=status, severity=severity, client_id=client_id, assigned_to_id=assigned_to_id)

@router.post("/{client_id}/issues", response_model=IssueRead)
async def create_issue(client_id: str, issue_in: IssueCreate, request: Request, background_tasks: BackgroundTasks, current_user: User = Depends(staff_checker)) -> Any:
    db_client = await Client.find_one(Client.id == client_id)
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    await _require_feature_access(current_user, "issue_create_roles", "You do not have permission to create issues")
    service = IssueService()
    return await service.create_issue(issue_in, client_id, current_user, request=request, background_tasks=background_tasks)

@router.get("/{client_id}/issues", response_model=List[IssueRead])
async def read_client_issues(client_id: str, current_user: User = Depends(staff_checker)) -> Any:
    db_client = await Client.find_one(Client.id == client_id)
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user and current_user.role != UserRole.ADMIN:
        has_access = (db_client.owner_id == current_user.id or db_client.pm_id == current_user.id or db_client.referred_by_id == current_user.id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")
    return await Issue.find(Issue.client_id == client_id, Issue.is_deleted != True).to_list()

@router.patch("/issues/{issue_id}", response_model=IssueRead)
async def update_issue(issue_id: str, issue_in: IssueUpdate, request: Request, current_user: User = Depends(staff_checker)) -> Any:
    await _require_feature_access(current_user, "issue_manage_roles", "You do not have permission to manage issues")
    service = IssueService()
    return await service.update_issue(issue_id, issue_in, current_user, request)

@router.delete("/issues/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issue(issue_id: str, request: Request, current_user: User = Depends(admin_checker)):
    await _require_feature_access(current_user, "issue_manage_roles", "You do not have permission to delete issues")
    service = IssueService()
    await service.delete_issue(issue_id, current_user, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@global_router.post("/batch-delete")
async def batch_delete_issues(ids: List[int], request: Request, current_user: User = Depends(admin_checker)):
    await _require_feature_access(current_user, "issue_manage_roles", "You do not have permission to delete issues")
    issues = await Issue.find(Issue.id.in_(ids)).to_list()
    for issue in issues:
        issue.is_deleted = True
        await issue.save()
    return {"message": f"Successfully deleted {len(issues)} issues"}

@router.get("/issues/{issue_id}", response_model=IssueRead)
async def get_issue_details(issue_id: str, current_user: User = Depends(staff_checker)) -> Any:
    db_issue = await Issue.find_one(Issue.id == issue_id)
    if not db_issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    service = IssueService()
    if not await service.can_access_issue(db_issue, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    db_client = await Client.find_one(Client.id == db_issue.client_id)
    if current_user and db_client and current_user.id == db_client.pm_id and db_issue.opened_at is None:
        db_issue.opened_at = datetime.now(timezone.utc)
        await db_issue.save()
    return db_issue
