from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.clients.models import Client
from app.modules.issues.models import Issue
from app.modules.issues.schemas import IssueCreate, IssueRead, IssueUpdate
from app.modules.issues.service import IssueService

router = APIRouter()

# Role definitions
admin_checker = RoleChecker([UserRole.ADMIN])
staff_checker = RoleChecker([
    UserRole.ADMIN, 
    UserRole.SALES, 
    UserRole.TELESALES, 
    UserRole.PROJECT_MANAGER, 
    UserRole.PROJECT_MANAGER_AND_SALES
])

@router.post("/{client_id}/issues", response_model=IssueRead)
async def create_issue(
    client_id: int,
    issue_in: IssueCreate,
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
    return await service.create_issue(issue_in, client_id, current_user, request=None, background_tasks=background_tasks)

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
def update_issue(
    issue_id: int,
    issue_in: IssueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    db_issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not db_issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Check client ownership if PM
    db_client = db.query(Client).filter(Client.id == db_issue.client_id).first()
    if current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    update_data = issue_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_issue, field, value)
    
    db.add(db_issue)
    db.commit()
    db.refresh(db_issue)
    return db_issue

    db_issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not db_issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    db.delete(db_issue)
    db.commit()
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

from app.modules.issues.schemas import IssueAssign

@router.patch("/issues/{issue_id}/assign", response_model=IssueRead)
def assign_issue(
    issue_id: int,
    assign_in: IssueAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    db_issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not db_issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Check access (PM or Admin only usually, or maybe Reporter? Restricting to PM/Admin for assignment)
    # staff_checker allows many roles. Let's refine if needed.
    # Logic: Only PM assigned to the client or Admin can assign?
    
    db_client = db.query(Client).filter(Client.id == db_issue.client_id).first()
    if current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Verify assignee
    assignee = db.query(User).filter(User.id == assign_in.assigned_to_id).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")

    db_issue.assigned_to_id = assign_in.assigned_to_id
    db.commit()
    db.refresh(db_issue)
    return db_issue
