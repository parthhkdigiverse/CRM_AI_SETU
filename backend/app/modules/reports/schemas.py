from pydantic import BaseModel

class DashboardStats(BaseModel):
    total_clients: int
    active_projects: int
    open_issues: int
    leads_by_status: dict

    class Config:
        from_attributes = True
