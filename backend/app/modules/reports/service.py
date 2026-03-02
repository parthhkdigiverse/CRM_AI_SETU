from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
import calendar
from app.modules.clients.models import Client
from app.modules.issues.models import Issue, IssueStatus, IssueSeverity
from app.modules.visits.models import Visit, VisitStatus
from app.modules.users.models import User
from app.modules.projects.models import Project, ProjectStatus
from app.modules.shops.models import Shop
from app.modules.payments.models import Payment, PaymentStatus

class ReportService:
    @staticmethod
    def get_dashboard_stats(db: Session):
        try:
            now = datetime.utcnow()
            curr_month = now.month
            curr_year = now.year
            
            if curr_month == 1:
                prev_month = 12
                prev_year = curr_year - 1
            else:
                prev_month = curr_month - 1
                prev_year = curr_year
                
            def get_mom_pct(curr_val, prev_val):
                if prev_val == 0:
                    return 100.0 if curr_val > 0 else 0.0
                return round(((curr_val - prev_val) / prev_val) * 100, 1)

            total_leads = db.query(func.count(Visit.id)).scalar() or 0
            leads_curr = db.query(func.count(Visit.id)).filter(extract('month', Visit.created_at) == curr_month, extract('year', Visit.created_at) == curr_year).scalar() or 0
            leads_prev = db.query(func.count(Visit.id)).filter(extract('month', Visit.created_at) == prev_month, extract('year', Visit.created_at) == prev_year).scalar() or 0
            leads_mom_pct = get_mom_pct(leads_curr, leads_prev)

            active_clients = db.query(func.count(Client.id)).filter(Client.is_active == True).scalar() or 0
            clients_curr = db.query(func.count(Client.id)).filter(Client.is_active == True, extract('month', Client.created_at) == curr_month, extract('year', Client.created_at) == curr_year).scalar() or 0
            clients_prev = db.query(func.count(Client.id)).filter(Client.is_active == True, extract('month', Client.created_at) == prev_month, extract('year', Client.created_at) == prev_year).scalar() or 0
            clients_mom_pct = get_mom_pct(clients_curr, clients_prev)

            ongoing_projects = db.query(func.count(Project.id)).filter(Project.status == ProjectStatus.IN_PROGRESS).scalar() or 0
            proj_curr = db.query(func.count(Project.id)).filter(extract('month', Project.created_at) == curr_month, extract('year', Project.created_at) == curr_year).scalar() or 0
            proj_prev = db.query(func.count(Project.id)).filter(extract('month', Project.created_at) == prev_month, extract('year', Project.created_at) == prev_year).scalar() or 0
            projects_mom_pct = get_mom_pct(proj_curr, proj_prev)

            revenue_mtd = db.query(func.sum(Payment.amount)).filter(Payment.status == PaymentStatus.VERIFIED, extract('month', Payment.verified_at) == curr_month, extract('year', Payment.verified_at) == curr_year).scalar() or 0.0
            revenue_prev = db.query(func.sum(Payment.amount)).filter(Payment.status == PaymentStatus.VERIFIED, extract('month', Payment.verified_at) == prev_month, extract('year', Payment.verified_at) == prev_year).scalar() or 0.0
            revenue_mom_pct = get_mom_pct(revenue_mtd, revenue_prev)

            open_issues = db.query(func.count(Issue.id)).filter(Issue.status.in_([IssueStatus.OPEN, IssueStatus.PENDING])).scalar() or 0

            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            
            monthly_visits = db.query(extract('month', Visit.visit_date).label('month'), func.count(Visit.id).label('count')).group_by('month').order_by('month').all()
            leads_by_month = {month_names[int(m)-1]: c for m, c in monthly_visits if m is not None and 1 <= int(m) <= 12}

            monthly_revenue = db.query(extract('month', Payment.verified_at).label('month'), func.sum(Payment.amount).label('total')).filter(Payment.status == PaymentStatus.VERIFIED).group_by('month').order_by('month').all()
            revenue_by_month = {month_names[int(m)-1]: float(t) for m, t in monthly_revenue if m is not None and 1 <= int(m) <= 12}

            visit_status_data = db.query(Visit.status, func.count(Visit.id)).group_by(Visit.status).all()
            visit_status_breakdown = {str(s.value if hasattr(s, 'value') else s): c for s, c in visit_status_data if s is not None}

            severity_data = db.query(Issue.severity, func.count(Issue.id)).group_by(Issue.severity).all()
            issue_severity_breakdown = {str(s.value if hasattr(s, 'value') else s): c for s, c in severity_data if s is not None}

            source_data = db.query(Shop.source, func.count(Shop.id)).group_by(Shop.source).all()
            lead_sources_breakdown = {str(s or 'Other'): c for s, c in source_data}

            return {
                "total_leads": total_leads,
                "active_clients": active_clients,
                "ongoing_projects": ongoing_projects,
                "revenue_mtd": float(revenue_mtd),
                "leads_mom_pct": leads_mom_pct,
                "clients_mom_pct": clients_mom_pct,
                "projects_mom_pct": projects_mom_pct,
                "revenue_mom_pct": revenue_mom_pct,
                "open_issues": open_issues,
                "leads_by_month": leads_by_month,
                "revenue_by_month": revenue_by_month,
                "visit_status_breakdown": visit_status_breakdown,
                "issue_severity_breakdown": issue_severity_breakdown,
                "lead_sources_breakdown": lead_sources_breakdown
            }

        except Exception as e:
            print(f"Dashboard Stats Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "total_leads": 0, "active_clients": 0, "ongoing_projects": 0, "revenue_mtd": 0.0,
                "leads_mom_pct": 0.0, "clients_mom_pct": 0.0, "projects_mom_pct": 0.0, "revenue_mom_pct": 0.0,
                "open_issues": 0, "leads_by_month": {}, "revenue_by_month": {}, 
                "visit_status_breakdown": {}, "issue_severity_breakdown": {}, "lead_sources_breakdown": {}
            }
