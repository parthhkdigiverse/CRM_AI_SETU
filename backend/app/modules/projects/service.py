# backend/app/modules/projects/service.py
from typing import Optional
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

    def get_projects(self, skip: int = 0, limit: int = 100, pm_id: Optional[int] = None):
        query = self.db.query(Project).filter(Project.is_deleted == False)
            
        if pm_id:
            query = query.filter(Project.pm_id == pm_id)
        
        projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
        
        # Calculate progress for each project
        from app.modules.issues.models import Issue, IssueStatus
        made_changes = False
        
        for p in projects:
            p.total_issues = self.db.query(Issue).filter(Issue.project_id == p.id, Issue.is_deleted == False).count()
            p.resolved_issues = self.db.query(Issue).filter(Issue.project_id == p.id, Issue.status == IssueStatus.RESOLVED, Issue.is_deleted == False).count()
            p.progress_percentage = (p.resolved_issues / p.total_issues * 100) if p.total_issues > 0 else 0.0
            
            # --- Silent Self-Healing: Sync Project PM with Client PM ---
            if p.client and p.client.pm_id and p.pm_id != p.client.pm_id:
                p.pm_id = p.client.pm_id
                made_changes = True

            # Populate names and contact info
            if p.client:
                p.client_name = p.client.name
                p.contact_person = p.client.name
                p.phone = p.client.phone
                p.email = p.client.email
                p.project_type = p.client.project_type
            if p.project_manager:
                p.pm_name = p.project_manager.name or p.project_manager.email
                
        if made_changes:
            self.db.commit()
            
        return projects

    def get_project(self, project_id: int):
        query = self.db.query(Project).filter(Project.id == project_id, Project.is_deleted == False)
        project = query.first()
        if project:
            from app.modules.issues.models import Issue, IssueStatus
            project.total_issues = self.db.query(Issue).filter(Issue.project_id == project_id, Issue.is_deleted == False).count()
            project.resolved_issues = self.db.query(Issue).filter(Issue.project_id == project_id, Issue.status == IssueStatus.RESOLVED, Issue.is_deleted == False).count()
            project.progress_percentage = (project.resolved_issues / project.total_issues * 100) if project.total_issues > 0 else 0.0
            
            # Populate names and contact info
            if project.client:
                project.client_name = project.client.name
                project.contact_person = project.client.name
                project.phone = project.client.phone
                project.email = project.client.email
                project.project_type = project.client.project_type
            if project.project_manager:
                project.pm_name = project.project_manager.name or project.project_manager.email
        return project


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
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        from app.modules.salary.models import AppSetting
        policy = self.db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
        is_hard = policy and policy.value == "HARD"

        old_data = {"name": project.name, "policy": "HARD" if is_hard else "SOFT"}
        
        if is_hard:
            self.db.delete(project)
        else:
            project.is_deleted = True
            
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
        return {"detail": f"Project {'permanently ' if is_hard else ''}deleted"}
