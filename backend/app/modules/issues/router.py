# backend/app/modules/issues/router.py
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, BackgroundTasks, Request
from sqlalchemy.orm import Session
import json
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.clients.models import Client
from app.modules.issues.models import Issue
from app.modules.salary.models import AppSetting
from app.modules.issues.schemas import IssueCreate, IssueRead, IssueUpdate
from app.modules.issues.service import IssueService

router = APIRouter()       # mounted at /clients prefix — handles /{client_id}/issues etc.
global_router = APIRouter() # mounted at /issues prefix — handles global GET /issues

# Role definitions
admin_checker = RoleChecker([UserRole.ADMIN])
staff_checker = RoleChecker([
    UserRole.ADMIN, 
    UserRole.SALES, 
    UserRole.TELESALES, 
    UserRole.PROJECT_MANAGER, 
    UserRole.PROJECT_MANAGER_AND_SALES
])


DEFAULT_FEATURE_ACCESS = {
    "issue_create_roles": ["ADMIN", "SALES", "TELESALES", "PROJECT_MANAGER", "PROJECT_MANAGER_AND_SALES"],
    "issue_manage_roles": ["ADMIN", "PROJECT_MANAGER", "PROJECT_MANAGER_AND_SALES", "SALES", "TELESALES"],
}


def _current_role_name(current_user: User) -> str:
    return current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)


def _get_feature_roles(db: Session, feature_key: str) -> set[str]:
    fallback = set(DEFAULT_FEATURE_ACCESS.get(feature_key, ["ADMIN"]))
    row = db.query(AppSetting).filter(AppSetting.key == "ui_access_policy").first()
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


def _require_feature_access(db: Session, current_user: User, feature_key: str, detail: str = "Access denied") -> None:
    role_name = _current_role_name(current_user).upper()
    if role_name not in _get_feature_roles(db, feature_key):
        raise HTTPException(status_code=403, detail=detail)

@global_router.get("/", response_model=List[IssueRead])
def read_global_issues(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    client_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    pm_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Global issue search with filters. PMs can only see issues for their assigned clients.
    """
    service = IssueService(db)
    if assigned_to_id is None and pm_id and pm_id not in {"ALL", "all"}:
        try:
            assigned_to_id = int(pm_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid pm_id")

    return service.get_all_issues_for_user(
        current_user=current_user,
        skip=skip, limit=limit, status=status, severity=severity, 
        client_id=client_id, assigned_to_id=assigned_to_id
    )

@router.post("/{client_id}/issues", response_model=IssueRead)
async def create_issue(
    client_id: int,
    issue_in: IssueCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Create an issue. Reporter is automatically set to current user.
    PMs can only report issues on their assigned clients.
    """
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")

    _require_feature_access(db, current_user, "issue_create_roles", "You do not have permission to create issues")
    
    # Relaxed: Any staff can report issues for any client
    # Original restriction (PMs only for their clients) is removed as per request for flexibility


    service = IssueService(db)
    return await service.create_issue(issue_in, client_id, current_user, request=request, background_tasks=background_tasks)

@router.get("/{client_id}/issues", response_model=List[IssueRead])
def read_client_issues(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    if current_user and current_user.role != UserRole.ADMIN:
        has_client_access = (
            db_client.owner_id == current_user.id
            or db_client.pm_id == current_user.id
            or db_client.referred_by_id == current_user.id
        )
        if not has_client_access:
            raise HTTPException(status_code=403, detail="Access denied")

    return db.query(Issue).filter(Issue.client_id == client_id).all()

@router.patch("/issues/{issue_id}", response_model=IssueRead)
async def update_issue(
    issue_id: int,
    issue_in: IssueUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    _require_feature_access(db, current_user, "issue_manage_roles", "You do not have permission to manage issues")

    service = IssueService(db)
    return await service.update_issue(issue_id, issue_in, current_user, request)

@router.delete("/issues/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issue(
    issue_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    _require_feature_access(db, current_user, "issue_manage_roles", "You do not have permission to delete issues")

    service = IssueService(db)
    await service.delete_issue(issue_id, current_user, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@global_router.post("/batch-delete")
async def batch_delete_issues(
    ids: List[int],
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    _require_feature_access(db, current_user, "issue_manage_roles", "You do not have permission to delete issues")

    try:
        db.query(Issue).filter(Issue.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        return {"message": f"Successfully deleted {len(ids)} issues"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/issues/{issue_id}", response_model=IssueRead)
def get_issue_details(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    db_issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not db_issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    service = IssueService(db)
    if not service.can_access_issue(db_issue, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    db_client = db.query(Client).filter(Client.id == db_issue.client_id).first()

    if current_user and db_client and current_user.id == db_client.pm_id and db_issue.opened_at is None:
        from datetime import datetime
        db_issue.opened_at = datetime.utcnow()
        db.commit()
        
    return db_issue

