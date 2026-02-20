from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request
from app.modules.projects.models import Project
from app.modules.projects.schemas import ProjectCreate, ProjectUpdate, ProjectAssign
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from app.modules.users.models import User

class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.activity_logger = ActivityLogger(db)

    def get_project(self, project_id: int):
        return self.db.query(Project).filter(Project.id == project_id).first()
    
    def get_projects(self, skip: int = 0, limit: int = 100, search: str = None, status_filter: str = None, client_id: int = None, sort_by: str = "created_at", sort_order: str = "desc"):
        query = self.db.query(Project)
        
        if search:
            query = query.filter(Project.name.ilike(f"%{search}%"))
        
        if status_filter:
            query = query.filter(Project.status == status_filter)

        if client_id:
            query = query.filter(Project.client_id == client_id)
            
        # Sorting Whitelist Hardening
        allowed_sort_fields = {"name", "created_at", "status"}
        
        if sort_by not in allowed_sort_fields:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid sort column. Allowed: {', '.join(allowed_sort_fields)}")

        if hasattr(Project, sort_by):
            column = getattr(Project, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
            
        return query.offset(skip).limit(limit).all()

    def create_project(self, project: ProjectCreate, current_user: User):
        from sqlalchemy import func
        from app.modules.users.models import UserRole
        from app.modules.projects.models import ProjectStatus

        pm_roles = [UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]
        active_statuses = [ProjectStatus.NEW, ProjectStatus.PLANNED, ProjectStatus.ONGOING]

        # Get PM with minimum active project count
        # Outer join to ensure PMs with 0 projects are included
        # Tie-breaker logic: order by count ASC, id ASC (oldest idle)
        workloads = self.db.query(
            User.id, func.count(Project.id).label('project_count')
        ).outerjoin(
            Project, (Project.pm_id == User.id) & (Project.status.in_(active_statuses))
        ).filter(
            User.role.in_(pm_roles),
            User.is_active == True
        ).group_by(
            User.id
        ).order_by(
            func.count(Project.id).asc(), User.id.asc()
        ).first()

        project_dict = project.model_dump()

        if workloads:
            project_dict['pm_id'] = workloads.id
        elif not project_dict.get('pm_id'):
            # Fallback if no PM found and none provided, though system should have PMs
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active Project Managers available for automatic assignment")

        db_project = Project(**project_dict)
        self.db.add(db_project)
        self.db.commit()
        self.db.refresh(db_project)
        return db_project

    async def update_project(self, project_id: int, project_update: ProjectUpdate, current_user: User, request: Request):
        db_project = self.get_project(project_id)
        if not db_project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        old_data = {
            "name": db_project.name,
            "description": db_project.description,
            "pm_id": db_project.pm_id, # Track PM specifically
            "client_id": db_project.client_id
             # Add status if/when implemented
        }

        update_data = project_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_project, key, value)

        self.db.commit()
        self.db.refresh(db_project)

        new_data = {k: getattr(db_project, k) for k in old_data.keys()}

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.UPDATE,
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            old_data=old_data,
            new_data=new_data,
            request=request
        )

        return db_project

    async def delete_project(self, project_id: int, current_user: User, request: Request):
        db_project = self.get_project(project_id)
        if not db_project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        
        old_data = {
            "name": db_project.name,
            "description": db_project.description
        }

        self.db.delete(db_project)
        self.db.commit()

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.DELETE,
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            old_data=old_data,
            new_data=None,
            request=request
        )

        return {"detail": "Project deleted"}

    async def assign_project_manager(self, project_id: int, assign_data: ProjectAssign, current_user: User, request: Request):
        db_project = self.get_project(project_id)
        if not db_project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        
        old_pm_id = db_project.pm_id
        
        db_project.pm_id = assign_data.pm_id
        self.db.commit()
        self.db.refresh(db_project)

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.ASSIGN, # Or REASSIGN
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            old_data={"pm_id": old_pm_id},
            new_data={"pm_id": assign_data.pm_id},
            request=request
        )
        return db_project
