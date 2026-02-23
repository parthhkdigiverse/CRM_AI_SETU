from sqlalchemy.orm import Session
from sqlalchemy import func
from app.modules.clients.models import Client
from app.modules.issues.models import Issue, IssueStatus

class ReportService:
    @staticmethod
    def get_dashboard_stats(db: Session):
        total_clients = db.query(func.count(Client.id)).scalar()
        
        active_projects = 0 # Deprecated
        
        open_issues = db.query(func.count(Issue.id)).filter(Issue.status == IssueStatus.OPEN).scalar()
        
        leads_by_status = {} # Deprecated
        
        return {
            "total_clients": total_clients or 0,
            "active_projects": active_projects,
            "open_issues": open_issues or 0,
            "leads_by_status": leads_by_status
        }
