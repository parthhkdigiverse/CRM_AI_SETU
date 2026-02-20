from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.projects.models import Project, ProjectStatus
from app.modules.projects.schemas import ProjectCreate, ProjectRead, ProjectUpdate, ProjectAssign, ProjectMemberCreate, ProjectMemberRead
from app.modules.projects.service import ProjectService
from app.modules.employees.models import Employee
from app.modules.projects.models import project_members

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
    service = ProjectService(db)
    return service.create_project(project_in, current_user)

@router.get("/", response_model=List[ProjectRead])
def read_projects(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[ProjectStatus] = None,
    client_id: Optional[int] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    View projects logic:
    - Admin/Sales: All projects
    - PM: Own projects
    """
    service = ProjectService(db)
    
    # If PM, filter by PM ID automatically
    # Note: Service currently doesn't support "my projects" filter directly, doing it here or need service update
    # Better to use service. The requirement was "filter by status", "search by name".
    # Access control logic for PMs needs to be preserved.
    
    if current_user.role in [UserRole.ADMIN, UserRole.SALES, UserRole.TELESALES, UserRole.PROJECT_MANAGER_AND_SALES]:
         return service.get_projects(
             skip=skip, 
             limit=limit, 
             search=search, 
             status_filter=status,
             client_id=client_id,
             sort_by=sort_by,
             sort_order=sort_order
         )
    
    # RESTRICTED TO PM
    # For now, let's fetch all (with filters) and then filter by PM in python or update service
    # Updating service to handle owner_id would be cleaner but for now let's reuse get_projects and filter if needed
    # OR, since we need pagination to work correctly, we MUST filter at DB level.
    
    # Custom query for PM
    query = db.query(Project).filter(Project.pm_id == current_user.id)
    if search:
        query = query.filter(Project.name.ilike(f"%{search}%"))
    if status:
        query = query.filter(Project.status == status)
    
    if client_id:
        query = query.filter(Project.client_id == client_id)

    # Sorting for PM
    if hasattr(Project, sort_by):
        column = getattr(Project, sort_by)
        if sort_order and sort_order.lower() == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        query = query.order_by(Project.created_at.desc())
        
    return query.offset(skip).limit(limit).all()

@router.get("/{project_id}", response_model=ProjectRead)
def read_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ProjectService(db)
    db_project = service.get_project(project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if current_user.role == UserRole.PROJECT_MANAGER and db_project.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this project")
        
    return db_project

@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    request: Request,
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    service = ProjectService(db)
    return await service.update_project(project_id, project_in, current_user, request)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    service = ProjectService(db)
    await service.delete_project(project_id, current_user, request)
    return None

@router.post("/{project_id}/assign", response_model=ProjectRead)
async def assign_project_manager(
    request: Request,
    project_id: int,
    assign_in: ProjectAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    """
    Assign/Reassign a Project Manager.
    """
    service = ProjectService(db)
    return await service.assign_project_manager(project_id, assign_in, current_user, request)


# Project Members logic (kept as is, but could be moved to service later)
@router.post("/{project_id}/members", response_model=ProjectMemberRead)
def add_project_member(
    project_id: int,
    member_in: ProjectMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker) 
) -> Any:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    employee = db.query(Employee).filter(Employee.id == member_in.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    query = project_members.select().where(
        (project_members.c.project_id == project_id) & 
        (project_members.c.employee_id == member_in.employee_id)
    )
    existing = db.execute(query).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Employee is already a member of this project")

    stmt = project_members.insert().values(
        project_id=project_id,
        employee_id=member_in.employee_id,
        role=member_in.role
    )
    db.execute(stmt)
    db.commit()
    
    return ProjectMemberRead(
        project_id=project_id,
        employee_id=member_in.employee_id,
        employee_name=employee.user.name if employee.user.name else employee.user.email,
        role=member_in.role
    )

@router.get("/{project_id}/members", response_model=List[ProjectMemberRead])
def list_project_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    results = db.query(
        project_members.c.project_id,
        project_members.c.employee_id,
        project_members.c.role,
        User.name,
        User.email
    ).join(
        Employee, Employee.id == project_members.c.employee_id
    ).join(
        User, User.id == Employee.user_id
    ).filter(
        project_members.c.project_id == project_id
    ).all()
    
    return [
        ProjectMemberRead(
            project_id=r.project_id,
            employee_id=r.employee_id,
            employee_name=r.name if r.name else r.email,
            role=r.role
        ) for r in results
    ]

@router.delete("/{project_id}/members/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member(
    project_id: int,
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    query = project_members.delete().where(
        (project_members.c.project_id == project_id) & 
        (project_members.c.employee_id == employee_id)
    )
    result = db.execute(query)
    db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Member not found in project")
        
    return None
