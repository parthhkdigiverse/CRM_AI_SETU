from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request
from app.modules.projects.models import Project
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

    async def create_project(self, project_in: ProjectCreate, current_user: User, request: Request):
        project_data = project_in.model_dump()
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
            new_data=project_in.model_dump(mode='json'),
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
