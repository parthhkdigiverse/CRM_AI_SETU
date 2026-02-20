from fastapi import APIRouter
from app.modules.auth import router as auth
from app.modules.clients import router as clients
from app.modules.projects import router as projects
from app.modules.issues import router as issues
from app.modules.meetings import router as meetings
from app.modules.employees import router as employees
from app.modules.feedback import router as feedback
from app.modules.salary import router as salary
from app.modules.incentives import router as incentives
from app.modules.activity_logs import router as activity_logs

# from app.api.routes import health # Keep health where it is or move it later

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
from app.modules.users import router as users
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(issues.router, prefix="/projects", tags=["issues"]) # Use project prefix for issues
api_router.include_router(meetings.router, prefix="/projects", tags=["meetings"]) # Use project prefix for meetings
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(feedback.router, prefix="/projects", tags=["feedback"])
api_router.include_router(salary.router, prefix="/hrm", tags=["salary_leave"])
api_router.include_router(incentives.router, prefix="/incentives", tags=["incentives"])
api_router.include_router(activity_logs.router, prefix="/activity-logs", tags=["activity_logs"])
from app.modules.leads import router as leads
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
from app.modules.areas import router as areas
api_router.include_router(areas.router, prefix="/areas", tags=["areas"])
from app.modules.visits import router as visits
api_router.include_router(visits.router, prefix="/visits", tags=["visits"])

@api_router.get("/health")
def health_check():
    return {"status": "ok"}
