from typing import Optional, List
from fastapi import HTTPException, status, Request, BackgroundTasks
from app.modules.issues.models import Issue
from app.modules.issues.schemas import IssueCreate, IssueUpdate
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from app.modules.users.models import User
from app.modules.clients.models import Client

class IssueService:
    def __init__(self):
        self.activity_logger = ActivityLogger()

    async def get_issue(self, issue_id: str):
        return await Issue.find_one(Issue.id == issue_id, Issue.is_deleted != True)

    async def get_all_issues(self, skip=0, limit=100, status=None, severity=None, client_id=None, assigned_to_id=None, pm_id=None):
        try:
            query_filter = [Issue.is_deleted != True]
            if client_id:
                query_filter.append(Issue.client_id == client_id)
            if assigned_to_id:
                query_filter.append(Issue.assigned_to_id == assigned_to_id)
            if severity:
                query_filter.append(Issue.severity == severity)
            issues = await Issue.find(*query_filter).sort(-Issue.id).skip(skip).limit(limit).to_list()
            if status:
                status_list = [s.strip() for s in status.split(',')]
                issues = [i for i in issues if str(i.status.value if hasattr(i.status, 'value') else i.status) in status_list]
            if pm_id:
                filtered = []
                for issue in issues:
                    client = await Client.find_one(Client.id == issue.client_id)
                    if client and client.pm_id == pm_id:
                        filtered.append(issue)
                issues = filtered
            await self._enrich_issues(issues)
            return issues
        except Exception as e:
            print(f"Error fetching issues: {e}")
            return []

    async def get_all_issues_for_user(self, current_user: User, skip=0, limit=100, status=None, severity=None, client_id=None, assigned_to_id=None):
        try:
            query_filter = [Issue.is_deleted != True]
            if client_id:
                query_filter.append(Issue.client_id == client_id)
            if assigned_to_id:
                query_filter.append(Issue.assigned_to_id == assigned_to_id)
            if severity:
                query_filter.append(Issue.severity == severity)
            issues = await Issue.find(*query_filter).sort(-Issue.id).skip(skip).limit(limit).to_list()
            if status:
                status_list = [s.strip() for s in status.split(',')]
                issues = [i for i in issues if str(i.status.value if hasattr(i.status, 'value') else i.status) in status_list]
            role_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
            if role_val != "ADMIN":
                filtered = []
                for issue in issues:
                    client = await Client.find_one(Client.id == issue.client_id)
                    has_access = (issue.assigned_to_id == current_user.id or issue.reporter_id == current_user.id or (client and (client.owner_id == current_user.id or client.pm_id == current_user.id or client.referred_by_id == current_user.id)))
                    if has_access:
                        filtered.append(issue)
                issues = filtered
            await self._enrich_issues(issues)
            return issues
        except Exception as e:
            print(f"Error fetching scoped issues: {e}")
            return []

    async def _enrich_issues(self, issues: list):
        for issue in issues:
            if issue.assigned_to_id:
                assigned_user = await User.find_one(User.id == issue.assigned_to_id)
                if assigned_user:
                    issue.pm_name = assigned_user.name or assigned_user.email or f"PM #{issue.assigned_to_id}"
            if issue.project_id:
                from app.modules.projects.models import Project
                project = await Project.find_one(Project.id == issue.project_id)
                if project:
                    issue.project_name = project.name
            if not getattr(issue, 'project_name', None) and issue.client_id:
                client = await Client.find_one(Client.id == issue.client_id)
                if client:
                    issue.project_name = client.name
            if issue.reporter_id:
                reporter = await User.find_one(User.id == issue.reporter_id)
                if reporter:
                    issue.reporter_name = reporter.name or reporter.email or f"User #{issue.reporter_id}"

    async def can_access_issue(self, issue: Issue, current_user: User) -> bool:
        role_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
        if role_val == "ADMIN":
            return True
        client = await Client.find_one(Client.id == issue.client_id)
        if not client:
            return issue.reporter_id == current_user.id or issue.assigned_to_id == current_user.id
        return (issue.assigned_to_id == current_user.id or issue.reporter_id == current_user.id or client.owner_id == current_user.id or client.pm_id == current_user.id or client.referred_by_id == current_user.id)

    async def can_update_issue(self, issue: Issue, current_user: User) -> bool:
        role_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
        if role_val == "ADMIN":
            return True
        return issue.assigned_to_id == current_user.id or issue.reporter_id == current_user.id

    async def create_issue(self, issue: IssueCreate, client_id: str, current_user: User, request: Request, background_tasks: BackgroundTasks = None):
        client = await Client.find_one(Client.id == client_id)
        issue_data = issue.model_dump(exclude_none=True)
        pm_id = issue_data.pop("assigned_to_id", None) or (client.pm_id if client else None)
        issue_data_clean = {k: v for k, v in issue_data.items() if k != "assigned_to_id"}
        db_issue = Issue(**issue_data_clean, client_id=client_id, reporter_id=current_user.id, assigned_to_id=pm_id)
        await db_issue.insert()
        await self.activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.CREATE, entity_type=EntityType.ISSUE, entity_id=db_issue.id, old_data=None, new_data=issue.model_dump(), request=request)
        try:
            from app.modules.notifications.service import EmailService
            email_service = EmailService()
            if client and client.pm_id:
                pm = await User.find_one(User.id == client.pm_id)
                if pm and background_tasks:
                    background_tasks.add_task(email_service.send_issue_notification, pm_email=pm.email, pm_name=pm.name, project_name=client.name, issue_title=db_issue.title, issue_description=db_issue.description, reporter_role=current_user.role)
        except Exception as e:
            print(f"Error scheduling email: {e}")
        return db_issue

    async def update_issue(self, issue_id: str, issue_update: IssueUpdate, current_user: User, request: Request):
        db_issue = await self.get_issue(issue_id)
        if not db_issue:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
        if not await self.can_update_issue(db_issue, current_user):
            raise HTTPException(status_code=403, detail="You can update only issues assigned to you or reported by you")
        old_data = {"title": db_issue.title, "description": db_issue.description, "status": db_issue.status.value if hasattr(db_issue.status, 'value') else str(db_issue.status), "assigned_to_id": db_issue.assigned_to_id}
        update_data = issue_update.model_dump(exclude_unset=True)
        if "status" in update_data:
            if "remarks" not in update_data or not update_data["remarks"] or not update_data["remarks"].strip():
                raise HTTPException(status_code=400, detail="Remarks are compulsory when updating an issue")
        for key, value in update_data.items():
            setattr(db_issue, key, value)
        db_issue.updated_at = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
        await db_issue.save()
        new_data = {k: getattr(db_issue, k) for k in old_data.keys()}
        new_data["status"] = new_data["status"].value if hasattr(new_data["status"], 'value') else str(new_data["status"])
        await self.activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.UPDATE, entity_type=EntityType.ISSUE, entity_id=issue_id, old_data=old_data, new_data=new_data, request=request)
        return db_issue

    async def delete_issue(self, issue_id: str, current_user: User, request: Request):
        db_issue = await Issue.find_one(Issue.id == issue_id)
        if not db_issue:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
        from app.modules.salary.models import AppSetting
        policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
        is_hard = policy and policy.value == "HARD"
        old_data = {"title": db_issue.title, "description": db_issue.description, "policy": "HARD" if is_hard else "SOFT"}
        if is_hard:
            await db_issue.delete()
        else:
            db_issue.is_deleted = True
            await db_issue.save()
        await self.activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.DELETE, entity_type=EntityType.ISSUE, entity_id=issue_id, old_data=old_data, new_data=None, request=request)
        return {"detail": f"Issue deleted"}
