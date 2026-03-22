from typing import List, Optional, Union, Any
from datetime import datetime, timedelta, timezone
from beanie.operators import In
import calendar
import io
import csv
import logging
from app.modules.clients.models import Client
from app.modules.issues.models import Issue, IssueSeverity
from app.modules.visits.models import Visit, VisitStatus
from app.modules.users.models import User, UserRole
from app.modules.projects.models import Project
from app.modules.shops.models import Shop
from app.core.enums import GlobalTaskStatus
from app.modules.payments.models import Payment, PaymentStatus
from app.modules.salary.models import SalarySlip
from app.modules.incentives.models import IncentiveSlip
from app.modules.reports.models import PerformanceNote
from app.modules.salary.models import AppSetting

logger = logging.getLogger(__name__)

class ReportService:

    async def get_dashboard_stats(self, requesting_user: User, area_id: Optional[str] = None, user_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None):
        if requesting_user.role != UserRole.ADMIN:
            user_id = requesting_user.id

        now = datetime.now(timezone.utc)
        curr_month = now.month
        curr_year = now.year
        
        if curr_month == 1:
            prev_month = 12; prev_year = curr_year - 1
        else:
            prev_month = curr_month - 1; prev_year = curr_year
            
        def get_mom_pct(curr_val, prev_val):
            if prev_val == 0: return 100.0 if curr_val > 0 else 0.0
            return round(((curr_val - prev_val) / prev_val) * 100, 1)

        async def get_filtered_count(model, date_field='created_at', user_field='owner_id', additional_filters=None, month=None, year=None):
            filters = additional_filters or []
            if area_id:
                if hasattr(model, 'area_id'): filters.append(model.area_id == area_id)
                elif model == Visit:
                    shops = await Shop.find(Shop.area_id == area_id).to_list()
                    shop_ids = [s.id for s in shops]
                    filters.append(In(Visit.shop_id, shop_ids))
            if user_id:
                if hasattr(model, user_field): filters.append(getattr(model, user_field) == user_id)
                elif model == Visit: filters.append(Visit.user_id == user_id)
            
            if month and year:
                # Approximate month/year filter for Beanie
                start = datetime(year, month, 1, tzinfo=timezone.utc)
                _, last_day = calendar.monthrange(year, month)
                end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
                filters.append(getattr(model, date_field) >= start)
                filters.append(getattr(model, date_field) <= end)
            else:
                if start_date: filters.append(getattr(model, date_field) >= datetime.fromisoformat(start_date))
                if end_date: filters.append(getattr(model, date_field) <= datetime.fromisoformat(end_date))
            
            return await model.find(*filters).count()

        total_visits = await get_filtered_count(Visit, 'visit_date', 'user_id')
        v_curr = await get_filtered_count(Visit, 'visit_date', 'user_id', month=curr_month, year=curr_year)
        v_prev = await get_filtered_count(Visit, 'visit_date', 'user_id', month=prev_month, year=prev_year)
        visits_mom_pct = get_mom_pct(v_curr, v_prev)

        active_clients = await get_filtered_count(Client, 'created_at', 'owner_id', [Client.is_active == True])
        c_curr = await get_filtered_count(Client, 'created_at', 'owner_id', [Client.is_active == True], month=curr_month, year=curr_year)
        c_prev = await get_filtered_count(Client, 'created_at', 'owner_id', [Client.is_active == True], month=prev_month, year=prev_year)
        clients_mom_pct = get_mom_pct(c_curr, c_prev)

        ongoing_projects = await get_filtered_count(Project, 'created_at', 'pm_id', [Project.status == GlobalTaskStatus.IN_PROGRESS])
        p_curr = await get_filtered_count(Project, 'created_at', 'pm_id', [Project.status == GlobalTaskStatus.IN_PROGRESS], month=curr_month, year=curr_year)
        p_prev = await get_filtered_count(Project, 'created_at', 'pm_id', [Project.status == GlobalTaskStatus.IN_PROGRESS], month=prev_month, year=prev_year)
        projects_mom_pct = get_mom_pct(p_curr, p_prev)

        # Revenue
        async def get_revenue(month, year):
            filters = [Payment.status == PaymentStatus.VERIFIED]
            start = datetime(year, month, 1, tzinfo=timezone.utc)
            _, last_day = calendar.monthrange(year, month)
            end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
            filters.append(Payment.verified_at >= start)
            filters.append(Payment.verified_at <= end)
            
            if requesting_user.role == UserRole.ADMIN:
                if area_id:
                    shops = await Shop.find(Shop.area_id == area_id).to_list()
                    client_ids = [s.id for s in shops] # Assuming client_id matches shop_id or resolve separately
                    filters.append(In(Payment.client_id, client_ids))
                if user_id: filters.append(Payment.generated_by_id == user_id)
            else:
                clients = await Client.find(Client.owner_id == requesting_user.id).to_list()
                filters.append(In(Payment.client_id, [c.id for c in clients]))
            
            payments = await Payment.find(*filters).to_list()
            return sum(p.amount for p in payments)

        revenue_mtd = await get_revenue(curr_month, curr_year)
        revenue_prev = await get_revenue(prev_month, prev_year)
        revenue_mom_pct = get_mom_pct(revenue_mtd, revenue_prev)

        open_issues = await get_filtered_count(Issue, 'created_at', 'assigned_user_id', [Issue.status == GlobalTaskStatus.OPEN])

        # Charts
        chart_title = "Visits by Day"
        visits_chart_data = {}
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        # Simplified chart logic for async
        all_visits = await Visit.find(Visit.is_deleted != True).sort(Visit.visit_date).to_list()
        from collections import defaultdict
        counts = defaultdict(int)
        for v in all_visits:
            if v.visit_date:
                fmt = v.visit_date.strftime('%d %b')
                counts[fmt] += 1
        visits_chart_data = dict(list(counts.items())[-7:]) # Last 7 days

        # Revenue Chart
        revenue_by_month = {}
        all_payments = await Payment.find(Payment.status == PaymentStatus.VERIFIED).to_list()
        rev_counts = defaultdict(float)
        for p in all_payments:
            if p.verified_at:
                m_name = month_names[p.verified_at.month - 1]
                rev_counts[m_name] += p.amount
        revenue_by_month = dict(rev_counts)

        # Breakdowns
        async def get_breakdown(model, field, filters=None):
            recs = await model.find(*(filters or [])).to_list()
            bd = defaultdict(int)
            for r in recs:
                val = getattr(r, field)
                val_str = str(val.value if hasattr(val, 'value') else val)
                bd[val_str] += 1
            return dict(bd)

        visit_status_breakdown = await get_breakdown(Visit, 'status', [Visit.is_deleted != True])
        issue_severity_breakdown = await get_breakdown(Issue, 'severity', [Issue.is_deleted != True])
        visit_outcomes_breakdown = visit_status_breakdown

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
            "visits_chart_title": chart_title,
            "visits_chart_data": visits_chart_data,
            "revenue_by_month": revenue_by_month,
            "visit_status_breakdown": visit_status_breakdown,
            "issue_severity_breakdown": issue_severity_breakdown,
            "visit_outcomes_breakdown": visit_outcomes_breakdown
        }

    async def get_employee_performance(self, requesting_user: User, month: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, user_id: Optional[Union[int, str]] = None):
        is_actually_admin = requesting_user.role == UserRole.ADMIN
        if not is_actually_admin: user_id = requesting_user.id
        elif user_id and str(user_id).lower() == 'all': user_id = None
        else:
            try: user_id = int(str(user_id)) if user_id else None
            except: user_id = None

        if not start_date and not end_date:
            if not month: month = datetime.now(timezone.utc).strftime('%Y-%m')
            year, m = map(int, month.split('-'))
            start_date = datetime(year, m, 1).strftime('%Y-%m-%d')
            _, last_day = calendar.monthrange(year, m)
            end_date = datetime(year, m, last_day).strftime('%Y-%m-%d')
        
        sd = datetime.fromisoformat(start_date) if start_date else None
        ed = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59) if end_date else None

        user_filter = [User.role != UserRole.CLIENT, User.is_deleted != True]
        if user_id: user_filter.append(User.id == user_id)
        users = await User.find(*user_filter).to_list()

        performance = []
        for u in users:
            v_filter = [Visit.user_id == u.id, Visit.is_deleted != True]
            if sd: v_filter.append(Visit.visit_date >= sd)
            if ed: v_filter.append(Visit.visit_date <= ed)
            total_v = await Visit.find(*v_filter).count()
            total_l = await Visit.find(*v_filter, Visit.status == VisitStatus.COMPLETED).count()
            
            p_filter = [Payment.generated_by_id == u.id, Payment.status == PaymentStatus.VERIFIED]
            if sd: p_filter.append(Payment.verified_at >= sd)
            if ed: p_filter.append(Payment.verified_at <= ed)
            payments = await Payment.find(*p_filter).to_list()
            revenue = sum(p.amount for p in payments)
            incentive_val = revenue * 0.05

            projects = await Project.find(Project.pm_id == u.id, Project.is_deleted != True).count()
            open_issues = await Issue.find(Issue.assigned_to_id == u.id, Issue.status != GlobalTaskStatus.RESOLVED, Issue.is_deleted != True).count()
            
            success_rate = (total_l / total_v * 100) if total_v > 0 else 0.0
            
            performance.append({
                "user_id": str(u.id), "id": str(u.id), "name": u.name or (u.email.split('@')[0] if u.email else 'Unknown'), "email": u.email or "",
                "role": u.role.value if hasattr(u.role, 'value') else str(u.role),
                "total_visits": total_v, "total_leads": total_l, "success_rate": round(success_rate, 1),
                "total_sales": float(revenue), "total_revenue": float(revenue), "total_incentive": float(incentive_val),
                "total_projects": projects, "total_open_issues": open_issues
            })
        
        return performance

    async def get_business_summary(self, month: Optional[str] = None):
        if not month: month = datetime.now(timezone.utc).strftime('%Y-%m')
        year, m = map(int, month.split('-'))
        start = datetime(year, m, 1, tzinfo=timezone.utc)
        _, last_day = calendar.monthrange(year, m)
        end = datetime(year, m, last_day, 23, 59, 59, tzinfo=timezone.utc)
        
        revenue_sum = sum([p.amount for p in await Payment.find(Payment.status == PaymentStatus.VERIFIED, Payment.verified_at >= start, Payment.verified_at <= end).to_list()])
        salaries = sum([s.final_salary for s in await SalarySlip.find(SalarySlip.month == month, SalarySlip.is_deleted != True).to_list()])
        incentives = sum([i.total_incentive for i in await IncentiveSlip.find(IncentiveSlip.period == month, IncentiveSlip.is_deleted != True).to_list()])
        clients = await Client.find(Client.created_at >= start, Client.created_at <= end, Client.is_deleted != True).count()
        visits = await Visit.find(Visit.visit_date >= start, Visit.visit_date <= end, Visit.is_deleted != True).count()
        issues = await Issue.find(Issue.created_at >= start, Issue.created_at <= end, Issue.is_deleted != True).count()
        
        total_expenses = salaries + incentives
        
        return {
            "month": month, "total_revenue": float(revenue_sum), "total_salaries": float(salaries),
            "total_incentives": float(incentives), "total_expenses": float(total_expenses),
            "net_profit": float(revenue_sum - total_expenses), "new_clients": clients,
            "total_visits": visits, "total_issues_raised": issues
        }

    async def get_project_portfolio(self, requesting_user: User, client_id: Optional[Union[int, str]] = None, status: Optional[str] = None, duration: Optional[str] = None):
        query_filter = [Project.is_deleted != True]
        if requesting_user.role != UserRole.ADMIN:
            clients = await Client.find(Client.owner_id == requesting_user.id).to_list()
            cids = [c.id for c in clients]
            query_filter.append({"$or": [{"pm_id": requesting_user.id}, {"client_id": {"$in": cids}}]})
        
        if client_id and str(client_id).lower() != 'all':
            try: query_filter.append(Project.client_id == int(client_id))
            except: pass
        if status and str(status).lower() != 'all':
            query_filter.append(Project.status == status)
        
        if duration and duration != 'all':
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(days=int(duration))
                query_filter.append(Project.updated_at >= cutoff)
            except: pass
            
        projects = await Project.find(*query_filter).to_list()
        portfolio = []
        
        for p in projects:
            client = await Client.find_one(Client.id == p.client_id)
            if not client: continue

            paid_sum = sum([pay.amount for pay in await Payment.find(Payment.client_id == p.client_id, Payment.status == PaymentStatus.VERIFIED).to_list()])
            
            last_visit = await Visit.find(In(Visit.shop_id, [p.client_id])).sort(-Visit.visit_date).find_one()

            p_val = str(p.priority.value if hasattr(p.priority, 'value') else p.priority)
            s_val = str(p.status.value if hasattr(p.status, 'value') else p.status)

            portfolio.append({
                "id": p.id, "fullName": client.name, "name": client.name,
                "org": client.organization or 'Individual', "project": p.name,
                "priority": p_val, "totalAmount": float(p.budget), "paidAmount": float(paid_sum),
                "outstanding": float(max(0.0, float(p.budget) - float(paid_sum))),
                "lastMeeting": last_visit.remarks if last_visit else "No recent interaction",
                "interactionDate": last_visit.visit_date if last_visit else p.created_at,
                "status": s_val
            })
            
        return portfolio

    async def get_employee_activities(self, user_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
        query_filter = [Visit.user_id == user_id, Visit.is_deleted != True]
        if start_date: query_filter.append(Visit.visit_date >= datetime.fromisoformat(start_date))
        if end_date: query_filter.append(Visit.visit_date <= datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59))
        visits = await Visit.find(*query_filter).sort(-Visit.visit_date).to_list()
        activities = []
        for v in visits:
            shop = await Shop.find_one(Shop.id == v.shop_id)
            activities.append({
                "date": v.visit_date,
                "client_name": shop.contact_person if shop and shop.contact_person else "Unknown Person",
                "client_details": shop.name if shop else "N/A",
                "project": shop.project_type if shop and shop.project_type else "General Project",
                "status": str(v.status.value if hasattr(v.status, 'value') else v.status)
            })
        return activities

    async def get_performance_notes(self, employee_id: str):
        return await PerformanceNote.find(PerformanceNote.employee_id == str(employee_id)).sort(-PerformanceNote.created_at).to_list()

    async def add_performance_note(self, employee_id: str, creator_id, note_text: str):
        note = PerformanceNote(employee_id=str(employee_id), created_by_id=str(creator_id), note=note_text)
        await note.insert()
        return note

    def generate_csv_response(self, data: List[dict]):
        if not data: return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
