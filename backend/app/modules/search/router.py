from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.search.service import SearchService
from app.core.dependencies import RoleChecker
from app.modules.users.models import UserRole

router = APIRouter()

# Allow all authenticated staff to search
staff_checker = RoleChecker([
    UserRole.ADMIN, 
    UserRole.SALES, 
    UserRole.TELESALES, 
    UserRole.PROJECT_MANAGER, 
    UserRole.PROJECT_MANAGER_AND_SALES
])

@router.get("/")
def global_search(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user = Depends(staff_checker)
):
    service = SearchService(db)
    return service.global_search(q)
