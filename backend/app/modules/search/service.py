from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Dict, Any

from app.modules.clients.models import Client
from app.modules.issues.models import Issue
from app.modules.projects.models import Project
from app.modules.employees.models import Employee
from app.modules.shops.models import Shop

from app.modules.users.models import User

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
                "leads": []
            }

        search_pattern = f"%{query}%"
        results = {}

        # 1. Search Clients
        clients = self.db.query(Client).filter(
            Client.is_active == True,
            or_(
                Client.name.ilike(search_pattern),
                Client.phone.ilike(search_pattern),
                Client.organization.ilike(search_pattern)
            )
        ).limit(limit).all()
        results["clients"] = [{"id": c.id, "name": c.name, "type": "client", "subtext": c.organization or c.phone} for c in clients]

        # 2. Search Issues
        issues = self.db.query(Issue).filter(
            or_(
                Issue.title.ilike(search_pattern),
                Issue.description.ilike(search_pattern)
            )
        ).limit(limit).all()
        results["issues"] = [{"id": i.id, "name": i.title, "type": "issue", "subtext": i.status.value if hasattr(i.status, 'value') else str(i.status)} for i in issues]

        # 3. Search Projects
        projects = self.db.query(Project).filter(
            Project.name.ilike(search_pattern)
        ).limit(limit).all()
        results["projects"] = [{"id": p.id, "name": p.name, "type": "project", "subtext": p.status.value if hasattr(p.status, 'value') else str(p.status)} for p in projects]

        # 4. Search Employees (Join with User for name/email)
        employees = self.db.query(User).join(Employee, Employee.user_id == User.id).filter(
            User.is_active == True,
            or_(
                User.name.ilike(search_pattern),
                User.email.ilike(search_pattern)
            )
        ).limit(limit).all()
        results["employees"] = [{"id": u.id, "name": u.name, "type": "employee", "subtext": u.role.value if hasattr(u.role, 'value') else str(u.role)} for u in employees]

        # 5. Search Leads (Shops)
        leads = self.db.query(Shop).filter(
            or_(
                Shop.name.ilike(search_pattern),
                Shop.address.ilike(search_pattern),
                Shop.contact_person.ilike(search_pattern)
            )
        ).limit(limit).all()
        results["leads"] = [{"id": l.id, "name": l.name, "type": "lead", "subtext": l.address} for l in leads]

        return results
