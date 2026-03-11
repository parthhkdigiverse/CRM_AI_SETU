# backend/app/modules/reports/schemas.py
from typing import Optional
from pydantic import BaseModel

class DashboardStats(BaseModel):
    total_visits: int
    active_clients: int
    ongoing_projects: int
    revenue_mtd: float
    
    visits_mom_pct: float
    clients_mom_pct: float
    projects_mom_pct: float
    revenue_mom_pct: float
    
    open_issues: int
    visits_by_month: dict
    revenue_by_month: dict
    visit_status_breakdown: dict
    issue_severity_breakdown: dict
    shop_sources_breakdown: dict

    class Config:
        from_attributes = True

class EmployeePerformance(BaseModel):
    user_id: int
    name: Optional[str]
    email: str
    role: str
    total_visits: int
    total_leads: int
    total_sales: int
    total_revenue: float
    total_incentive: float

class BusinessSummary(BaseModel):
    month: str
    total_revenue: float
    total_salaries: float
    total_incentives: float
    total_expenses: float
    net_profit: float
    new_clients: int
    total_visits: int
    total_issues_raised: int
