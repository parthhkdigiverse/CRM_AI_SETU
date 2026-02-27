from fastapi import APIRouter
from app.modules.auth import router as auth
from app.modules.issues import router as issues
from app.modules.issues.router import global_router as issues_global_router
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
from app.modules.clients import router as clients
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(issues.router, prefix="/clients", tags=["issues"]) # Moved from projects to clients
api_router.include_router(issues_global_router, prefix="/issues", tags=["issues"]) # Global issues route at /issues
api_router.include_router(meetings.router, prefix="/clients", tags=["meetings"]) # Moved from projects to clients
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(feedback.router, prefix="/clients", tags=["feedback"])
api_router.include_router(salary.router, prefix="/hrm", tags=["salary_leave"])
api_router.include_router(incentives.router, prefix="/incentives", tags=["incentives"])
api_router.include_router(activity_logs.router, prefix="/activity-logs", tags=["activity_logs"])
from app.modules.areas import router as areas
api_router.include_router(areas.router, prefix="/areas", tags=["areas"])
from app.modules.visits import router as visits
api_router.include_router(visits.router, prefix="/visits", tags=["visits"])

from app.modules.shops import router as shops
api_router.include_router(shops.router, prefix="/shops", tags=["shops"])

from app.modules.reports import router as reports
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

from app.modules.payments import router as payments
api_router.include_router(payments.router, tags=["payments"]) # We omit prefix, as paths are custom (clients/{id}/payments)

from app.modules.projects import router as projects
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])

from app.modules.todos import router as todos
api_router.include_router(todos.router, prefix="/todos", tags=["todos"])

from app.modules.notifications import router as notifications
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])

from app.modules.billing import router as billing
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])

from app.modules.timetable import router as timetable
api_router.include_router(timetable.router, prefix="/timetable", tags=["timetable"])

from app.modules.idcards import router as idcards
api_router.include_router(idcards.router, prefix="/idcards", tags=["idcards"])

@api_router.get("/health")
def health_check():
    return {"status": "ok"}
