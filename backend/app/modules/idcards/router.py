from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import UserRole
from app.modules.idcards.service import IDCardService
from app.modules.idcards.schemas import IDCardData

router = APIRouter()
pro_checker = RoleChecker([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])

@router.get("/{employee_id}", response_model=IDCardData)
def get_id_card(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(pro_checker)
):
    service = IDCardService(db)
    return service.get_id_card_data(employee_id)
