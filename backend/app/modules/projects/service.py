from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request
from app.modules.projects.models import Project, ProjectStatus
from app.modules.projects.schemas import ProjectCreate, ProjectUpdate
from app.modules.users.models import User, UserRole
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType

class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.activity_logger = ActivityLogger(db)

    def get_project(self, project_id: int):
        return self.db.query(Project).filter(Project.id == project_id).first()

    def get_projects(self, skip: int = 0, limit: int = 100, pm_id: int = None):
        query = self.db.query(Project)
        if pm_id:
            query = query.filter(Project.pm_id == pm_id)
        return query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()

    def get_least_busy_pm(self) -> Optional[int]:
        """Find the PM with the lowest number of active projects (PLANNING or IN_PROGRESS)."""
        pm_users = self.db.query(User).filter(
            User.role.in_([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]),
            User.is_active == True,
            User.is_deleted == False
        ).all()

        if not pm_users:
            return None

        pm_workloads = []
        for pm in pm_users:
            workload = self.db.query(Project).filter(
                Project.pm_id == pm.id,
                Project.status.in_([ProjectStatus.PLANNING, ProjectStatus.IN_PROGRESS])
            ).count()
            pm_workloads.append((pm.id, workload))

        # Sort by workload and return ID of PM with least projects
        pm_workloads.sort(key=lambda x: x[1])
        return pm_workloads[0][0]

    async def create_project(self, project_in: ProjectCreate, current_user: User, request: Request):
        project_data = project_in.model_dump()
        
        # Automatic PM assignment if not provided
        if not project_data.get("pm_id"):
            pm_id = self.get_least_busy_pm()
            if pm_id:
                project_data["pm_id"] = pm_id
            else:
                # Fallback if no PM found - could either throw error or use current user if they are a PM
                if current_user.role in [UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]:
                    project_data["pm_id"] = current_user.id
                else:
                    # Search for any ADMIN as ultra-fallback or raise error
                    admin_user = self.db.query(User).filter(User.role == UserRole.ADMIN).first()
                    if admin_user:
                        project_data["pm_id"] = admin_user.id
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No available Project Manager found for assignment."
                        )

        project = Project(**project_data)
        
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.CREATE,
            entity_type=EntityType.PROJECT,
            entity_id=project.id,
            new_data=project_data,
            request=request
        )
        return project

    async def update_project(self, project_id: int, project_in: ProjectUpdate, current_user: User, request: Request):
        project = self.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        old_data = {"status": project.status.value, "name": project.name}
        
        update_data = project_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        self.db.commit()
        self.db.refresh(project)

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.UPDATE,
            entity_type=EntityType.PROJECT,
            entity_id=project.id,
            old_data=old_data,
            new_data=update_data,
            request=request
        )
        return project

    async def delete_project(self, project_id: int, current_user: User, request: Request):
        project = self.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        old_data = {"name": project.name}
        self.db.delete(project)
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
