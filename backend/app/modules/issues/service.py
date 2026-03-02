from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request
from app.modules.issues.models import Issue
from app.modules.issues.schemas import IssueCreate, IssueUpdate
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.modules.notifications.service import EmailService
from fastapi import BackgroundTasks

class IssueService:
    def __init__(self, db: Session):
        self.db = db
        self.activity_logger = ActivityLogger(db)

    def get_issue(self, issue_id: int):
        return self.db.query(Issue).filter(Issue.id == issue_id).first()

    def get_issues(self, skip: int = 0, limit: int = 100):
        return self.db.query(Issue).offset(skip).limit(limit).all()

    def get_all_issues(self, skip: int = 0, limit: int = 100, status=None, severity=None, client_id=None, assigned_to_id=None, pm_id=None):
        query = self.db.query(Issue)
        if pm_id: 
            query = query.join(Client).filter(Client.pm_id == pm_id)
        if status:
            query = query.filter(Issue.status == status)
        if severity:
            query = query.filter(Issue.severity == severity)
        if client_id:
            query = query.filter(Issue.client_id == client_id)
        if assigned_to_id:
            query = query.filter(Issue.assigned_to_id == assigned_to_id)
            
        issues = query.order_by(Issue.id.desc()).offset(skip).limit(limit).all()
        
        # Populate logical properties manually since SQLA joins can be complex for simple Pydantic dicts
        for issue in issues:
            if issue.assigned_to:
                issue.pm_name = issue.assigned_to.name
            if issue.project:
                issue.project_name = issue.project.name
            elif issue.client:
                # Fallback to Client name if no specific project
                issue.project_name = issue.client.name
            if issue.reporter:
                issue.reporter_name = issue.reporter.name
            
        return issues

    async def create_issue(self, issue: IssueCreate, client_id: int, current_user: User, request: Request, background_tasks: BackgroundTasks = None):
        client = self.db.query(Client).filter(Client.id == client_id).first()
        pm_id = client.pm_id if client else None
        db_issue = Issue(**issue.model_dump(), client_id=client_id, reporter_id=current_user.id, assigned_to_id=pm_id)

        self.db.add(db_issue)
        self.db.commit()
        self.db.refresh(db_issue)

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.CREATE,
            entity_type=EntityType.ISSUE,
            entity_id=db_issue.id,
            old_data=None,
            new_data=issue.model_dump(),

            request=request
        )

        # Trigger Email Notification
        try:
            email_service = EmailService()
            client = self.db.query(Client).filter(Client.id == db_issue.client_id).first()
            if client and client.pm and background_tasks:
                background_tasks.add_task(
                    email_service.send_issue_notification,
                    pm_email=client.pm.email,
                    pm_name=client.pm.name,
                    project_name=client.name, # Using client name as context
                    issue_title=db_issue.title,
                    issue_description=db_issue.description,
                    reporter_role=current_user.role
                )
            elif client and client.pm:
                # Fallback if no background_tasks provided (e.g. tests)
                email_service.send_issue_notification(
                    pm_email=client.pm.email,
                    pm_name=client.pm.name,
                    project_name=client.name, # Using client name as context
                    issue_title=db_issue.title,
                    issue_description=db_issue.description,
                    reporter_role=current_user.role
                )
        except Exception as e:
            print(f"Error scheduling email: {e}")

        return db_issue

    async def update_issue(self, issue_id: int, issue_update: IssueUpdate, current_user: User, request: Request):
        db_issue = self.get_issue(issue_id)
        if not db_issue:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

        old_data = {
            "title": db_issue.title,
            "description": db_issue.description,
            "status": db_issue.status.value if hasattr(db_issue.status, 'value') else str(db_issue.status),
            "assigned_to_id": db_issue.assigned_to_id
        }

        update_data = issue_update.model_dump(exclude_unset=True)

        if "status" in update_data:
            if "remarks" not in update_data or not update_data["remarks"] or not update_data["remarks"].strip():
                raise HTTPException(status_code=400, detail="Remarks are compulsory when updating an issue")

        for key, value in update_data.items():
            setattr(db_issue, key, value)

        self.db.commit()
        self.db.refresh(db_issue)

        new_data = {k: getattr(db_issue, k) for k in old_data.keys()}
        # Handle enum serialization
        new_data["status"] = new_data["status"].value if hasattr(new_data["status"], 'value') else str(new_data["status"])

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.UPDATE,
            entity_type=EntityType.ISSUE,
            entity_id=issue_id,
            old_data=old_data,
            new_data=new_data,
            request=request
        )

        return db_issue

    async def delete_issue(self, issue_id: int, current_user: User, request: Request):
        db_issue = self.get_issue(issue_id)
        if not db_issue:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

        old_data = {
            "title": db_issue.title,
            "description": db_issue.description
        }

        self.db.delete(db_issue)
        self.db.commit()

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.DELETE,
            entity_type=EntityType.ISSUE,
            entity_id=issue_id,
            old_data=old_data,
            new_data=None,
            request=request
        )

        return {"detail": "Issue deleted"}
