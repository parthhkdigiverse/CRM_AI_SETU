from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String, desc, case
from typing import List, Dict, Any

from app.modules.clients.models import Client
from app.modules.issues.models import Issue
from app.modules.projects.models import Project
from app.modules.shops.models import Shop
from app.modules.users.models import User
from app.modules.payments.models import Payment
from app.modules.areas.models import Area
from app.modules.meetings.models import MeetingSummary

class SearchService:
    def __init__(self, db: Session):
        self.db = db

    def global_search(self, query: str, limit: int = 15) -> Dict[str, List[Dict[str, Any]]]:
        if not query or len(query) < 2:
            return {
                "clients": [],
                "issues": [],
                "projects": [],
                "employees": [],
                "leads": [],
                "payments": [],
                "areas": [],
                "meetings": []
            }

        search_pattern = f"%{query}%"
        # For relevance sorting: exact match or starts with query gets higher priority
        exact_pattern = f"{query}%"
        results = {}

        # Helper to apply relevance sorting (exact/start match first)
        def apply_relevance(query_obj, field):
            return query_obj.order_by(
                case(
                    (field.ilike(exact_pattern), 0),
                    else_=1
                )
            )

        # 1. Search Clients
        q_clients = self.db.query(Client).filter(
            Client.is_active == True,
            or_(
                Client.name.ilike(search_pattern),
                Client.phone.ilike(search_pattern),
                Client.organization.ilike(search_pattern)
            )
        )
        clients = apply_relevance(q_clients, Client.name).limit(limit).all()
        results["clients"] = [{"id": c.id, "name": c.name, "type": "client", "subtext": c.organization or c.phone} for c in clients]

        # 2. Search Issues
        q_issues = self.db.query(Issue).filter(
            or_(
                Issue.title.ilike(search_pattern),
                Issue.description.ilike(search_pattern)
            )
        )
        issues = apply_relevance(q_issues, Issue.title).limit(limit).all()
        results["issues"] = [{"id": i.id, "name": i.title, "type": "issue", "subtext": i.status.value if hasattr(i.status, 'value') else str(i.status)} for i in issues]

        # 3. Search Projects
        q_projects = self.db.query(Project).filter(
            Project.name.ilike(search_pattern)
        )
        projects = apply_relevance(q_projects, Project.name).limit(limit).all()
        results["projects"] = [{"id": p.id, "name": p.name, "type": "project", "subtext": p.status.value if hasattr(p.status, 'value') else str(p.status)} for p in projects]

        # 4. Search Users (employees)
        q_users = self.db.query(User).filter(
            User.is_active == True,
            User.is_deleted == False,
            or_(
                User.name.ilike(search_pattern),
                User.email.ilike(search_pattern)
            )
        )
        employees = apply_relevance(q_users, User.name).limit(limit).all()
        results["employees"] = [{"id": u.id, "name": u.name, "type": "employee", "subtext": u.role.value if hasattr(u.role, 'value') else str(u.role)} for u in employees]

        # 5. Search Leads (Shops)
        q_leads = self.db.query(Shop).filter(
            or_(
                Shop.name.ilike(search_pattern),
                Shop.address.ilike(search_pattern),
                Shop.contact_person.ilike(search_pattern)
            )
        )
        leads = apply_relevance(q_leads, Shop.name).limit(limit).all()
        results["leads"] = [{"id": l.id, "name": l.name, "type": "lead", "subtext": l.address} for l in leads]

        # 6. Search Payments
        payments = self.db.query(Payment).filter(
            or_(
                cast(Payment.amount, String).ilike(search_pattern),
                cast(Payment.status, String).ilike(search_pattern)
            )
        ).limit(limit).all()
        results["payments"] = [{"id": p.id, "name": f"Payment: ₹{p.amount}", "type": "payment", "subtext": f"Status: {p.status.value if hasattr(p.status, 'value') else str(p.status)}"} for p in payments]

        # 7. Search Areas
        q_areas = self.db.query(Area).filter(
            or_(
                Area.name.ilike(search_pattern),
                Area.pincode.ilike(search_pattern),
                Area.city.ilike(search_pattern)
            )
        )
        areas = apply_relevance(q_areas, Area.name).limit(limit).all()
        results["areas"] = [{"id": a.id, "name": a.name, "type": "area", "subtext": f"{a.city or ''} {a.pincode or ''}".strip()} for a in areas]

        # 8. Search Meetings
        q_meetings = self.db.query(MeetingSummary).filter(
            or_(
                MeetingSummary.title.ilike(search_pattern),
                MeetingSummary.content.ilike(search_pattern)
            )
        )
        meetings = apply_relevance(q_meetings, MeetingSummary.title).limit(limit).all()
        results["meetings"] = [{"id": m.id, "name": m.title, "type": "meeting", "subtext": m.date.strftime('%d %b %Y') if m.date else ""} for m in meetings]

        return results
