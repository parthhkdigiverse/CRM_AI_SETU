from typing import List, Dict, Any, Optional
import re
from beanie import Document

from app.modules.clients.models import Client
from app.modules.issues.models import Issue
from app.modules.projects.models import Project
from app.modules.shops.models import Shop
from app.modules.users.models import User
from app.modules.payments.models import Payment
from app.modules.areas.models import Area
from app.modules.meetings.models import MeetingSummary

class SearchService:
    def __init__(self):
        # MongoDB (Beanie) ma DB session ni jarur nathi hoy
        pass

    async def global_search(self, query: str, limit: int = 15) -> Dict[str, List[Dict[str, Any]]]:
        if not query or len(query) < 2:
            return {
                "clients": [], "issues": [], "projects": [],
                "employees": [], "leads": [], "payments": [],
                "areas": [], "meetings": []
            }

        # MongoDB regex search (Case-insensitive)
        search_re = {"$regex": re.escape(query), "$options": "i"}
        results = {}

        # 1. Search Clients
        clients = await Client.find(
            Client.is_active == True,
            {"$or": [
                {"name": search_re},
                {"phone": search_re},
                {"organization": search_re}
            ]}
        ).limit(limit).to_list()
        results["clients"] = [{"id": str(c.id), "name": c.name, "type": "client", "subtext": c.organization or c.phone} for c in clients]

        # 2. Search Issues
        issues = await Issue.find(
            {"$or": [{"title": search_re}, {"description": search_re}]}
        ).limit(limit).to_list()
        results["issues"] = [{"id": str(i.id), "name": i.title, "type": "issue", "subtext": str(i.status)} for i in issues]

        # 3. Search Projects
        projects = await Project.find({"name": search_re}).limit(limit).to_list()
        results["projects"] = [{"id": str(p.id), "name": p.name, "type": "project", "subtext": str(p.status)} for p in projects]

        # 4. Search Users (employees)
        users = await User.find(
            User.is_active == True,
            User.is_deleted == False,
            {"$or": [{"name": search_re}, {"email": search_re}]}
        ).limit(limit).to_list()
        results["employees"] = [{"id": str(u.id), "name": u.name, "type": "employee", "subtext": str(u.role)} for u in users]

        # 5. Search Leads (Shops)
        shops = await Shop.find(
            {"$or": [
                {"name": search_re},
                {"address": search_re},
                {"contact_person": search_re}
            ]}
        ).limit(limit).to_list()
        results["leads"] = [{"id": str(s.id), "name": s.name, "type": "lead", "subtext": s.address} for s in shops]

        # 6. Search Payments
        # MongoDB ma amount (Number) par regex direct nathi chaltu, etle search_re handle karvu pade
        payments = await Payment.find(
            {"$or": [{"status": search_re}]} 
        ).limit(limit).to_list()
        results["payments"] = [{"id": str(p.id), "name": f"Payment: ₹{p.amount}", "type": "payment", "subtext": f"Status: {p.status}"} for p in payments]

        # 7. Search Areas
        areas = await Area.find(
            {"$or": [
                {"name": search_re},
                {"pincode": search_re},
                {"city": search_re}
            ]}
        ).limit(limit).to_list()
        results["areas"] = [{"id": str(a.id), "name": a.name, "type": "area", "subtext": f"{a.city or ''} {a.pincode or ''}".strip()} for a in areas]

        # 8. Search Meetings
        meetings = await MeetingSummary.find(
            {"$or": [{"title": search_re}, {"content": search_re}]}
        ).limit(limit).to_list()
        results["meetings"] = [{"id": str(m.id), "name": m.title, "type": "meeting", "subtext": m.date.strftime('%d %b %Y') if m.date else ""} for m in meetings]

        return results