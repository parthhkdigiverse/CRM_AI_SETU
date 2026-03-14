from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract
from datetime import datetime, timedelta
import calendar
from app.modules.clients.models import Client
from app.modules.issues.models import Issue, IssueStatus, IssueSeverity
from app.modules.visits.models import Visit, VisitStatus
from app.modules.users.models import User, UserRole
from app.modules.projects.models import Project, ProjectStatus
from app.modules.shops.models import Shop
from app.modules.payments.models import Payment, PaymentStatus
from app.modules.salary.models import SalarySlip
from app.modules.incentives.models import IncentiveSlip
import io
import csv
from typing import List, Optional, Union, Any

class ReportService:
    @staticmethod
    def get_dashboard_stats(
        db: Session, 
        requesting_user: User,
        area_id: Optional[int] = None, 
        user_id: Optional[int] = None, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ):
        # RBAC: Non-admins can only see their own stats
        if requesting_user.role != UserRole.ADMIN:
            user_id = requesting_user.id

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

            def apply_filters(query, model, date_field='created_at', user_field='owner_id'):
                if area_id and hasattr(model, 'area_id'):
                    query = query.filter(model.area_id == area_id)
                elif area_id and model == Visit:
                    # Visits are linked to shops, shops are linked to areas
                    query = query.join(Shop, Visit.shop_id == Shop.id).filter(Shop.area_id == area_id)
                
                if user_id:
                    if hasattr(model, user_field):
                        query = query.filter(getattr(model, user_field) == user_id)
                    elif model == Visit:
                        query = query.filter(Visit.user_id == user_id)
                
                if start_date:
                    query = query.filter(getattr(model, date_field) >= start_date)
                if end_date:
                    query = query.filter(getattr(model, date_field) <= end_date)
                return query

            # Total Visits
            visit_query = db.query(func.count(Visit.id))
            visit_query = apply_filters(visit_query, Visit, 'visit_date', 'user_id')
            total_visits = visit_query.scalar() or 0
            
            v_curr = db.query(func.count(Visit.id)).filter(extract('month', Visit.visit_date) == curr_month, extract('year', Visit.visit_date) == curr_year)
            v_curr = apply_filters(v_curr, Visit, 'visit_date', 'user_id').scalar() or 0
            
            v_prev = db.query(func.count(Visit.id)).filter(extract('month', Visit.visit_date) == prev_month, extract('year', Visit.visit_date) == prev_year)
            v_prev = apply_filters(v_prev, Visit, 'visit_date', 'user_id').scalar() or 0
            visits_mom_pct = get_mom_pct(v_curr, v_prev)

            # Active Clients
            client_query = db.query(func.count(Client.id)).filter(Client.is_active == True)
            client_query = apply_filters(client_query, Client, 'created_at', 'owner_id')
            active_clients = client_query.scalar() or 0
            
            c_curr = db.query(func.count(Client.id)).filter(Client.is_active == True, extract('month', Client.created_at) == curr_month, extract('year', Client.created_at) == curr_year)
            c_curr = apply_filters(c_curr, Client, 'created_at', 'owner_id').scalar() or 0
            
            c_prev = db.query(func.count(Client.id)).filter(Client.is_active == True, extract('month', Client.created_at) == prev_month, extract('year', Client.created_at) == prev_year)
            c_prev = apply_filters(c_prev, Client, 'created_at', 'owner_id').scalar() or 0
            clients_mom_pct = get_mom_pct(c_curr, c_prev)

            # Ongoing Projects
            project_query = db.query(func.count(Project.id)).filter(Project.status == ProjectStatus.IN_PROGRESS)
            # Projects are linked to clients, clients to owners/areas
            if area_id or user_id:
                project_query = project_query.join(Client, Project.client_id == Client.id)
                project_query = apply_filters(project_query, Client, 'created_at', 'owner_id')
            else:
                project_query = apply_filters(project_query, Project, 'created_at', 'pm_id')
            ongoing_projects = project_query.scalar() or 0
            
            p_curr = db.query(func.count(Project.id)).filter(extract('month', Project.created_at) == curr_month, extract('year', Project.created_at) == curr_year)

            # Project MoM (re-implementing based on new RBAC logic)
            def get_project_count_for_month(db_session, month, year, user, area_id, user_id_filter):
                q = db_session.query(func.count(Project.id)).filter(
                    extract('month', Project.created_at) == month,
                    extract('year', Project.created_at) == year
                )
                if user.role == UserRole.ADMIN:
                    if area_id:
                        q = q.join(Client).filter(Client.area_id == area_id)
                    if user_id_filter:
                        q = q.filter(Project.pm_id == user_id_filter)
                elif user.role in [UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]:
                    q = q.filter(Project.pm_id == user.id)
                else:
                    q = q.join(Client).filter(Client.owner_id == user.id)
                return q.scalar() or 0

            p_curr = get_project_count_for_month(db, curr_month, curr_year, requesting_user, area_id, user_id)
            p_prev = get_project_count_for_month(db, prev_month, prev_year, requesting_user, area_id, user_id)
            projects_mom_pct = get_mom_pct(p_curr, p_prev)

            # Revenue MTD
            rev_query = db.query(func.sum(Payment.amount)).filter(
                Payment.status == PaymentStatus.VERIFIED, 
                extract('month', Payment.verified_at) == curr_month, 
                extract('year', Payment.verified_at) == curr_year
            )
            
            if requesting_user.role == UserRole.ADMIN:
                if area_id:
                    rev_query = rev_query.join(Client).filter(Client.area_id == area_id)
                if user_id:
                    rev_query = rev_query.filter(Payment.generated_by_id == user_id)
            else:
                # Non-admins see revenue from their owned clients
                rev_query = rev_query.join(Client).filter(Client.owner_id == requesting_user.id)
            
            revenue_mtd = rev_query.scalar() or 0.0
            
            # Revenue Prev Month (for trend)
            rev_prev_q = db.query(func.sum(Payment.amount)).filter(
                Payment.status == PaymentStatus.VERIFIED, 
                extract('month', Payment.verified_at) == prev_month, 
                extract('year', Payment.verified_at) == prev_year
            )
            if requesting_user.role == UserRole.ADMIN:
                if area_id: rev_prev_q = rev_prev_q.join(Client).filter(Client.area_id == area_id)
                if user_id: rev_prev_q = rev_prev_q.filter(Payment.generated_by_id == user_id)
            else:
                rev_prev_q = rev_prev_q.join(Client).filter(Client.owner_id == requesting_user.id)
            
            revenue_prev = rev_prev_q.scalar() or 0.0
            revenue_mom_pct = get_mom_pct(revenue_mtd, revenue_prev)

            # Open Issues
            open_issues_query = db.query(func.count(Issue.id)).filter(Issue.status.in_([IssueStatus.PENDING]))
            open_issues_query = apply_filters(open_issues_query, Issue, 'created_at', 'assigned_user_id')
            open_issues = open_issues_query.scalar() or 0

            # Charts logic
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            
            mv_query = db.query(extract('month', Visit.visit_date).label('month'), func.count(Visit.id).label('count'))
            mv_query = apply_filters(mv_query, Visit, 'visit_date', 'user_id').group_by('month').order_by('month')
            monthly_visits = mv_query.all()
            visits_by_month = {month_names[int(m)-1]: c for m, c in monthly_visits if m and 1 <= int(m) <= 12}

            mr_query = db.query(extract('month', Payment.verified_at).label('month'), func.sum(Payment.amount).label('total')).filter(Payment.status == PaymentStatus.VERIFIED)
            if requesting_user.role != UserRole.ADMIN:
                mr_query = mr_query.join(Client).filter(Client.owner_id == requesting_user.id)
            else:
                mr_query = apply_filters(mr_query, Payment, 'verified_at', 'generated_by_id')
            
            mr_query = mr_query.group_by('month').order_by('month')
            monthly_revenue = mr_query.all()
            revenue_by_month = {month_names[int(m)-1]: float(t) for m, t in monthly_revenue if m and 1 <= int(m) <= 12}

            vs_query = db.query(Visit.status, func.count(Visit.id))
            vs_query = apply_filters(vs_query, Visit, 'visit_date', 'user_id').group_by(Visit.status)
            visit_status_data = vs_query.all()
            visit_status_breakdown = {str(s.value if hasattr(s, 'value') else s): c for s, c in visit_status_data if s is not None}

            is_query = db.query(Issue.severity, func.count(Issue.id))
            is_query = apply_filters(is_query, Issue, 'created_at', 'assigned_user_id').group_by(Issue.severity)
            severity_data = is_query.all()
            issue_severity_breakdown = {str(s.value if hasattr(s, 'value') else s): c for s, c in severity_data if s is not None}

            ss_query = db.query(Shop.source, func.count(Shop.id))
            if user_id: ss_query = ss_query.filter(Shop.owner_id == user_id)
            if area_id: ss_query = ss_query.filter(Shop.area_id == area_id)
            source_data = ss_query.group_by(Shop.source).all()
            shop_sources_breakdown = {str(s or 'Other'): c for s, c in source_data}

            return {
                "total_visits": total_visits,
                "active_clients": active_clients,
                "ongoing_projects": ongoing_projects,
                "revenue_mtd": float(revenue_mtd),
                "visits_mom_pct": visits_mom_pct,
                "clients_mom_pct": clients_mom_pct,
                "projects_mom_pct": projects_mom_pct,
                "revenue_mom_pct": revenue_mom_pct,
                "open_issues": open_issues,
                "visits_by_month": visits_by_month,
                "revenue_by_month": revenue_by_month,
                "visit_status_breakdown": visit_status_breakdown,
                "issue_severity_breakdown": issue_severity_breakdown,
                "shop_sources_breakdown": shop_sources_breakdown
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "total_visits": 0, "active_clients": 0, "ongoing_projects": 0, "revenue_mtd": 0.0,
                "visits_mom_pct": 0.0, "clients_mom_pct": 0.0, "projects_mom_pct": 0.0, "revenue_mom_pct": 0.0,
                "open_issues": 0, "visits_by_month": {}, "revenue_by_month": {}, 
                "visit_status_breakdown": {}, "issue_severity_breakdown": {}, "shop_sources_breakdown": {}
            }

    @staticmethod
    def get_employee_performance(
        db: Session, 
        requesting_user: User,
        month: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: Optional[Union[int, str]] = None
    ):
        # RBAC: Non-admins can only see their own performance metrics
        if requesting_user.role != UserRole.ADMIN:
            user_id = requesting_user.id
        elif user_id and str(user_id).lower() == 'all':
            user_id = None
        elif user_id:
            try:
                user_id = int(user_id)
            except ValueError:
                user_id = None

        if not start_date and not end_date:
            if not month:
                month = datetime.utcnow().strftime('%Y-%m')
            
            try:
                year, m = map(int, month.split('-'))
                start_date = datetime(year, m, 1).strftime('%Y-%m-%d')
                last_day = calendar.monthrange(year, m)[1]
                end_date = datetime(year, m, last_day).strftime('%Y-%m-%d')
            except:
                start_date = None
                end_date = None
        
        v_sub = db.query(
            Visit.user_id,
            func.count(Visit.id).label('total_visits'),
            func.count(Visit.id).filter(Visit.status == VisitStatus.COMPLETED).label('total_leads')
        )
        if start_date: v_sub = v_sub.filter(Visit.visit_date >= start_date)
        if end_date: v_sub = v_sub.filter(Visit.visit_date <= end_date)
        v_sub = v_sub.group_by(Visit.user_id).subquery()

        p_sub = db.query(
            Payment.generated_by_id,
            func.sum(Payment.amount).label('total_revenue')
        ).filter(Payment.status == PaymentStatus.VERIFIED)
        if start_date: p_sub = p_sub.filter(Payment.verified_at >= start_date)
        if end_date: p_sub = p_sub.filter(Payment.verified_at <= end_date)
        p_sub = p_sub.group_by(Payment.generated_by_id).subquery()

        query = db.query(
            User,
            func.coalesce(v_sub.c.total_visits, 0).label('v_count'),
            func.coalesce(v_sub.c.total_leads, 0).label('l_count'),
            func.coalesce(p_sub.c.total_revenue, 0.0).label('revenue')
        ).filter(User.role != 'CLIENT', User.is_deleted == False)

        if user_id:
            query = query.filter(User.id == user_id)

        query = query.outerjoin(v_sub, User.id == v_sub.c.user_id)
        query = query.outerjoin(p_sub, User.id == p_sub.c.generated_by_id)

        results = query.all()
        performance = []
        
        for row in results:
            u, visits, leads, revenue = row
            # Calculate 5% incentive as requested
            incentive_val = float(revenue) * 0.05
        for u in users:
            visits = db.query(func.count(Visit.id)).filter(
                Visit.user_id == u.id,
                extract('year', Visit.visit_date) == year,
                extract('month', Visit.visit_date) == m
            ).scalar() or 0
            
            leads = db.query(func.count(Visit.id)).filter(
                Visit.user_id == u.id,
                Visit.status.in_(['ACCEPT', 'SATISFIED']),
                extract('year', Visit.visit_date) == year,
                extract('month', Visit.visit_date) == m
            ).scalar() or 0
            
            payments = db.query(func.count(Payment.id)).filter(
                Payment.generated_by_id == u.id,
                Payment.status == PaymentStatus.VERIFIED,
                extract('year', Payment.verified_at) == year,
                extract('month', Payment.verified_at) == m
            ).scalar() or 0
            
            revenue = db.query(func.sum(Payment.amount)).filter(
                Payment.generated_by_id == u.id,
                Payment.status == PaymentStatus.VERIFIED,
                extract('year', Payment.verified_at) == year,
                extract('month', Payment.verified_at) == m
            ).scalar() or 0.0
            
            incentive = db.query(IncentiveSlip.total_incentive).filter(
                IncentiveSlip.user_id == u.id,
                IncentiveSlip.period == month
            ).scalar() or 0.0

            projects = db.query(func.count(Project.id)).filter(
                Project.pm_id == u.id
            ).scalar() or 0

            open_issues = db.query(func.count(Issue.id)).filter(
                Issue.assigned_to_id == u.id,
                Issue.status.notin_([IssueStatus.SOLVED, IssueStatus.RESOLVED, IssueStatus.COMPLETED, IssueStatus.CANCELLED])
            ).scalar() or 0
            
            performance.append({
                "user_id": u.id,
                "id": u.id,
                "name": u.name or u.email.split('@')[0],
                "email": u.email,
                "role": str(u.role),
                "total_visits": int(visits),
                "total_leads": int(leads),
                "total_sales": float(revenue),
                "total_revenue": float(revenue),
                "total_incentive": float(incentive_val),
                "total_incentive": float(incentive),
                "total_projects": projects,
                "total_open_issues": open_issues
            })
        
        return performance

    @staticmethod
    def get_business_summary(db: Session, month: Optional[str] = None):
        if not month:
            month = datetime.utcnow().strftime('%Y-%m')
        
        year, m = map(int, month.split('-'))
        
        revenue = db.query(func.sum(Payment.amount)).filter(
            Payment.status == PaymentStatus.VERIFIED,
            extract('year', Payment.verified_at) == year,
            extract('month', Payment.verified_at) == m
        ).scalar() or 0.0
        
        salaries = db.query(func.sum(SalarySlip.final_salary)).filter(
            SalarySlip.month == month
        ).scalar() or 0.0
        
        incentives = db.query(func.sum(IncentiveSlip.total_incentive)).filter(
            IncentiveSlip.period == month
        ).scalar() or 0.0
        
        clients = db.query(func.count(Client.id)).filter(
            extract('year', Client.created_at) == year,
            extract('month', Client.created_at) == m
        ).scalar() or 0
        
        visits = db.query(func.count(Visit.id)).filter(
            extract('year', Visit.visit_date) == year,
            extract('month', Visit.visit_date) == m
        ).scalar() or 0
        
        issues = db.query(func.count(Issue.id)).filter(
            extract('year', Issue.created_at) == year,
            extract('month', Issue.created_at) == m
        ).scalar() or 0
        
        total_expenses = salaries + incentives
        
        return {
            "month": month,
            "total_revenue": float(revenue),
            "total_salaries": float(salaries),
            "total_incentives": float(incentives),
            "total_expenses": float(total_expenses),
            "net_profit": float(revenue - total_expenses),
            "new_clients": clients,
            "total_visits": visits,
            "total_issues_raised": issues
        }

    @staticmethod
    def get_project_portfolio(
        db: Session,
        requesting_user: User,
        client_id: Optional[Union[int, str]] = None,
        status: Optional[str] = None,
        duration: Optional[str] = None
    ):
        query = db.query(Project).options(joinedload(Project.client))

        # RBAC: Non-admins only see assigned clients/projects
        if requesting_user.role != UserRole.ADMIN:
            query = query.join(Client, Project.client_id == Client.id).filter(
                (Project.pm_id == requesting_user.id) | 
                (Client.owner_id == requesting_user.id)
            )
        
        if client_id and str(client_id).lower() != 'all':
            try:
                cid = int(client_id)
                query = query.filter(Project.client_id == cid)
            except ValueError:
                pass # Ignore invalid numeric filter values
        if status and str(status).lower() != 'all':
            query = query.filter(Project.status == status)
        
        if duration and duration != 'all':
            try:
                days = int(duration)
                cutoff = datetime.utcnow() - timedelta(days=days)
                query = query.filter(Project.updated_at >= cutoff)
            except ValueError:
                pass
            
        projects = query.all()
        portfolio = []
        
        for p in projects:
            if not p.client:
                continue

            # Get total paid amount for this client/project
            paid_sum = db.query(func.sum(Payment.amount)).filter(
                Payment.client_id == p.client_id,
                Payment.status == PaymentStatus.VERIFIED
            ).scalar() or 0.0
            
            # Get last interaction (visit)
            last_visit = None
            if p.client.owner_id:
                last_visit = db.query(Visit).filter(
                    Visit.shop_id.in_(db.query(Shop.id).filter(Shop.owner_id == p.client.owner_id))
                ).order_by(Visit.visit_date.desc()).first()

            # Ensure naive datetimes to avoid mixing aware/naive
            def ensure_naive(dt):
                if not dt: return datetime.utcnow()
                return dt.replace(tzinfo=None) if hasattr(dt, 'replace') else dt

            iDate = ensure_naive(last_visit.visit_date if last_visit and last_visit.visit_date else p.created_at)

            # Safer priority/status extraction
            p_val = "MEDIUM"
            if p.priority:
                p_val = str(p.priority.value if hasattr(p.priority, 'value') else p.priority)
            
            s_val = "PLANNING"
            if p.status:
                s_val = str(p.status.value if hasattr(p.status, 'value') else p.status)

            portfolio.append({
                "id": p.id,
                "fullName": p.client.name or "Unnamed Client", 
                "name": p.client.name or "Unnamed Client",
                "org": getattr(p.client, 'organization', 'Individual') or 'Individual',
                "project": p.name or "Unnamed Project",
                "priority": p_val,
                "totalAmount": float(p.budget or 0),
                "paidAmount": float(paid_sum),
                "outstanding": float(max(0, (float(p.budget or 0) - float(paid_sum)))),
                "lastMeeting": last_visit.remarks if last_visit and last_visit.remarks else "No recent interaction",
                "interactionDate": iDate,
                "status": s_val
            })
            
        return portfolio

    @staticmethod
    def get_employee_activities(
        db: Session,
        user_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ):
        query = db.query(Visit).filter(Visit.user_id == user_id)
        
        if start_date:
            query = query.filter(Visit.visit_date >= start_date)
        if end_date:
            query = query.filter(Visit.visit_date <= end_date)
            
        visits = query.order_by(Visit.visit_date.desc()).all()
        activities = []
        
        for v in visits:
            activities.append({
                "date": v.visit_date,
                "client": v.shop.name if v.shop else "Unknown",
                "type": v.remarks[:30] + "..." if v.remarks and len(v.remarks) > 30 else (v.remarks or "Site Visit"),
                "status": str(v.status.value if hasattr(v.status, 'value') else v.status)
            })
            
        return activities

    @staticmethod
    def generate_csv_response(data: List[dict]):
        if not data:
            return ""
            
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
