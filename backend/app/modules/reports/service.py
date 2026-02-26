from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.modules.clients.models import Client
from app.modules.issues.models import Issue, IssueStatus, IssueSeverity
from app.modules.visits.models import Visit, VisitStatus

class ReportService:
    @staticmethod
    def get_dashboard_stats(db: Session):
        try:
            total_leads = db.query(func.count(Visit.id)).scalar() or 0
            active_clients = db.query(func.count(Client.id)).filter(Client.is_active == True).scalar() or 0
            ongoing_projects = db.query(func.count(Client.id)).filter(Client.pm_id != None).scalar() or 0
            open_issues = db.query(func.count(Issue.id)).filter(Issue.status == IssueStatus.OPEN).scalar() or 0

            # Leads by Month (for Bar Chart)
            monthly_data = db.query(
                extract('month', Visit.visit_date).label('month'),
                func.count(Visit.id).label('count')
            ).group_by('month').order_by('month').all()
            
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            leads_by_month = {}
            for m, c in monthly_data:
                if m is not None:
                    try:
                        idx = int(m) - 1
                        if 0 <= idx < 12:
                            leads_by_month[month_names[idx]] = c
                    except (ValueError, TypeError):
                        continue

            # Visit Status Breakdown (for Donut Chart)
            visit_status_data = db.query(Visit.status, func.count(Visit.id)).group_by(Visit.status).all()
            visit_status_breakdown = {str(s.value if hasattr(s, 'value') else s): c for s, c in visit_status_data if s is not None}

            # Issue Severity Breakdown (for Donut Chart)
            severity_data = db.query(Issue.severity, func.count(Issue.id)).group_by(Issue.severity).all()
            issue_severity_breakdown = {str(s.value if hasattr(s, 'value') else s): c for s, c in severity_data if s is not None}

            return {
                "total_leads": total_leads,
                "active_clients": active_clients,
                "ongoing_projects": ongoing_projects,
                "open_issues": open_issues,
                "leads_by_month": leads_by_month,
                "visit_status_breakdown": visit_status_breakdown,
                "issue_severity_breakdown": issue_severity_breakdown
            }

        except Exception as e:
            print(f"Dashboard Stats Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "total_leads": 0, "active_clients": 0, "ongoing_projects": 0, "open_issues": 0,
                "leads_by_month": {}, "visit_status_breakdown": {}, "issue_severity_breakdown": {}
            }
