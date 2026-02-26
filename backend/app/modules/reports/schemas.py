from pydantic import BaseModel

class DashboardStats(BaseModel):
    total_leads: int
    active_clients: int
    ongoing_projects: int
    open_issues: int
    leads_by_month: dict
    visit_status_breakdown: dict
    issue_severity_breakdown: dict

    class Config:
        from_attributes = True
