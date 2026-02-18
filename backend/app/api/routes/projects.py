from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker, get_current_active_user
from app.models.user import User, UserRole
from app.models.crm import Project, Issue, MeetingSummary, IssueStatus
from app.schemas.crm import (
    ProjectCreate, ProjectRead, ProjectUpdate,
    IssueCreate, IssueRead, IssueUpdate,
    MeetingSummaryCreate, MeetingSummaryRead
)

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
pm_checker = RoleChecker([
    UserRole.ADMIN, 
    UserRole.PROJECT_MANAGER, 
    UserRole.PROJECT_MANAGER_AND_SALES
])

# --- Project Routes ---

@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    *,
    db: Session = Depends(get_db),
    project_in: ProjectCreate,
    current_user: User = Depends(admin_checker)
) -> Any:
    """
    Create a new project. Admins only.
    """
    db_project = Project(**project_in.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.get("/", response_model=List[ProjectRead])
def read_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    View projects logic:
    - Admin: All projects
    - PM: Own project
    - Sales/Telesales: All projects
    """
    if current_user.role in [UserRole.ADMIN, UserRole.SALES, UserRole.TELESALES, UserRole.PROJECT_MANAGER_AND_SALES]:
        return db.query(Project).all()
    
    # Simple PM view
    return db.query(Project).filter(Project.pm_id == current_user.id).all()

# --- Issue Routes ---

@router.post("/{project_id}/issues", response_model=IssueRead)
def create_issue(
    project_id: int,
    issue_in: IssueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    db_issue = Issue(**issue_in.model_dump(), project_id=project_id)
    db.add(db_issue)
    db.commit()
    db.refresh(db_issue)
    return db_issue

# --- Meeting Summary Routes ---

@router.post("/{project_id}/meetings", response_model=MeetingSummaryRead)
def create_meeting(
    project_id: int,
    meeting_in: MeetingSummaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_checker)
) -> Any:
    db_meeting = MeetingSummary(**meeting_in.model_dump(), project_id=project_id)
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
    return db_meeting
