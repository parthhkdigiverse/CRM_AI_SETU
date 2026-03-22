from fastapi import APIRouter, Depends, Query
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
async def global_search(
    q: str = Query(..., min_length=2),
    current_user = Depends(staff_checker)
):
    # Beanie ma session pass karvani jarur nathi
    service = SearchService()
    return await service.global_search(q)