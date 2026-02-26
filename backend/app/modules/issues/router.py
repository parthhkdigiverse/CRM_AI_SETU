from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.clients.models import Client
from app.modules.issues.models import Issue
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

@global_router.get("/", response_model=List[IssueRead])
def read_global_issues(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    client_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Global issue search with filters. PMs can only see issues for their assigned clients.
    """
    service = IssueService(db)
    pm_id = current_user.id if current_user.role == UserRole.PROJECT_MANAGER else None
    
    return service.get_all_issues(
        skip=skip, limit=limit, status=status, severity=severity, 
        client_id=client_id, assigned_to_id=assigned_to_id, pm_id=pm_id
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
    
    if current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only report issues for your assigned clients")

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
        
    if current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
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
    service = IssueService(db)
    return await service.update_issue(issue_id, issue_in, current_user, request)

@router.delete("/issues/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issue(
    issue_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    service = IssueService(db)
    await service.delete_issue(issue_id, current_user, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/issues/{issue_id}", response_model=IssueRead)
def get_issue_details(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    db_issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not db_issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Check access (PM check)
    db_client = db.query(Client).filter(Client.id == db_issue.client_id).first()
    if current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    return db_issue

