from pydantic import BaseModel

class DashboardStats(BaseModel):
    total_leads: int
    active_clients: int
    ongoing_projects: int
    revenue_mtd: float
    
    leads_mom_pct: float
    clients_mom_pct: float
    projects_mom_pct: float
    revenue_mom_pct: float
    
    open_issues: int
    leads_by_month: dict
    revenue_by_month: dict
    visit_status_breakdown: dict
    issue_severity_breakdown: dict
    lead_sources_breakdown: dict

    class Config:
        from_attributes = True
