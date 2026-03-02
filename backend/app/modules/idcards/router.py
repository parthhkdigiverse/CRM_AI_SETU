from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import UserRole
from app.modules.idcards.service import IDCardService
from app.modules.idcards.schemas import IDCardData

router = APIRouter()
pro_checker = RoleChecker([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES, UserRole.SALES, UserRole.TELESALES])

@router.get("/view_own", response_class=HTMLResponse)
def view_own_id_card(
    db: Session = Depends(get_db),
    current_user = Depends(pro_checker)
):
    service = IDCardService(db)
    return service.generate_id_card_html_by_user(current_user.id)

@router.get("/{employee_id}/view", response_class=HTMLResponse)
def view_id_card(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(pro_checker)
):
    service = IDCardService(db)
    return service.generate_id_card_html(employee_id)
