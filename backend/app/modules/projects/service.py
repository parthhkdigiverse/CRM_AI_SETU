from typing import Optional
from fastapi import HTTPException, status, Request
from app.modules.projects.models import Project
from app.core.enums import GlobalTaskStatus
from app.modules.projects.schemas import ProjectCreate, ProjectUpdate
from app.modules.users.models import User, UserRole
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType

class ProjectService:
    def __init__(self):
        self.activity_logger = ActivityLogger()

    async def _enrich_project(self, p: Project):
        from app.modules.issues.models import Issue
        from app.modules.clients.models import Client
        issues = await Issue.find(Issue.project_id == str(p.id), Issue.is_deleted != True).to_list()
        p.total_issues = len(issues)
        p.resolved_issues = len([i for i in issues if i.status == GlobalTaskStatus.RESOLVED])
        p.progress_percentage = (p.resolved_issues / p.total_issues * 100) if p.total_issues > 0 else 0.0
        if p.client_id:
            client = await Client.find_one(Client.id == p.client_id)
            if client:
                p.client_name = client.name
                p.contact_person = client.name
                p.phone = client.phone
                p.email = client.email
                p.project_type = client.project_type
        if p.pm_id:
            pm = await User.find_one(User.id == p.pm_id)
            if pm:
                p.pm_name = pm.name or pm.email

    async def get_projects(self, skip: int = 0, limit: int = 100, pm_id: Optional[str] = None):
        query_filter = [Project.is_deleted != True]
        if pm_id:
            query_filter.append(Project.pm_id == pm_id)
        projects = await Project.find(*query_filter).sort(-Project.created_at).skip(skip).limit(limit).to_list()
        for p in projects:
            await self._enrich_project(p)
        return projects

    async def get_project(self, project_id: str):
        project = await Project.find_one(Project.id == project_id, Project.is_deleted != True)
        if project:
            await self._enrich_project(project)
        return project

    async def get_least_busy_pm(self) -> Optional[int]:
        pm_users = await User.find(User.role.in_([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]), User.is_active == True, User.is_deleted != True).to_list()
        if not pm_users:
            return None
        pm_workloads = []
        for pm in pm_users:
            workload = await Project.find(Project.pm_id == pm.id, Project.status.in_([GlobalTaskStatus.OPEN, GlobalTaskStatus.IN_PROGRESS])).count()
            pm_workloads.append((pm.id, workload))
        pm_workloads.sort(key=lambda x: x[1])
        return pm_workloads[0][0]

    async def create_project(self, project_in: ProjectCreate, current_user: User, request: Request):
        project_data = project_in.model_dump()
        if not project_data.get("pm_id"):
            pm_id = await self.get_least_busy_pm()
            if pm_id:
                project_data["pm_id"] = pm_id
            elif current_user.role in [UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]:
                project_data["pm_id"] = current_user.id
            else:
                admin_user = await User.find_one(User.role == UserRole.ADMIN)
                if admin_user:
                    project_data["pm_id"] = admin_user.id
                else:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No available Project Manager found for assignment.")
        project = Project(**project_data)
        await project.insert()
        await self.activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.CREATE, entity_type=EntityType.PROJECT, entity_id=project.id, new_data=project_data, request=request)
        return project

    async def update_project(self, project_id: str, project_in: ProjectUpdate, current_user: User, request: Request):
        project = await self.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        old_data = {"status": project.status.value if hasattr(project.status, 'value') else str(project.status), "name": project.name}
        update_data = project_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        await project.save()
        await self.activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.UPDATE, entity_type=EntityType.PROJECT, entity_id=project.id, old_data=old_data, new_data=update_data, request=request)
        return project

    async def delete_project(self, project_id: str, current_user: User, request: Request):
        project = await Project.find_one(Project.id == project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        from app.modules.salary.models import AppSetting
        policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
        is_hard = policy and policy.value == "HARD"
        old_data = {"name": project.name, "policy": "HARD" if is_hard else "SOFT"}
        if is_hard:
            await project.delete()
        else:
            project.is_deleted = True
            await project.save()
        await self.activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.DELETE, entity_type=EntityType.PROJECT, entity_id=project_id, old_data=old_data, new_data=None, request=request)
        return {"detail": f"Project deleted"}
