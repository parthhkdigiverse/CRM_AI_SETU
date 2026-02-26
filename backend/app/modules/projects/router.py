from typing import List, Any, Optional
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.projects.schemas import ProjectCreate, ProjectRead, ProjectUpdate
from app.modules.projects.service import ProjectService

router = APIRouter()

admin_access = RoleChecker([UserRole.ADMIN])
staff_access = RoleChecker([
    UserRole.ADMIN, 
    UserRole.SALES, 
    UserRole.TELESALES, 
    UserRole.PROJECT_MANAGER, 
    UserRole.PROJECT_MANAGER_AND_SALES
])
pm_access = RoleChecker([
    UserRole.ADMIN, 
    UserRole.PROJECT_MANAGER, 
    UserRole.PROJECT_MANAGER_AND_SALES
])

@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: Request,
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_access)
) -> Any:
    service = ProjectService(db)
    return await service.create_project(project_in, current_user, request)

@router.get("/", response_model=List[ProjectRead])
def read_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access)
) -> Any:
    service = ProjectService(db)
    # PMs only see their own projects, Admins and Sales can see all (or configure as needed)
    pm_id = current_user.id if current_user.role in [UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES] else None
    return service.get_projects(skip=skip, limit=limit, pm_id=pm_id)

@router.get("/{project_id}", response_model=ProjectRead)
def read_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access)
) -> Any:
    service = ProjectService(db)
    project = service.get_project(project_id)
    from fastapi import HTTPException
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    request: Request,
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_access)
) -> Any:
    service = ProjectService(db)
    return await service.update_project(project_id, project_in, current_user, request)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_access)
) -> None:
    service = ProjectService(db)
    await service.delete_project(project_id, current_user, request)
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)
