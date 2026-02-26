from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.billing.schemas import BillCreate, BillRead
from app.modules.billing.service import BillingService

router = APIRouter()

# Access for Sales, Telesales and Admins
staff_access = RoleChecker([
    UserRole.ADMIN, 
    UserRole.SALES, 
    UserRole.TELESALES
])

@router.post("/", response_model=BillRead, status_code=status.HTTP_201_CREATED)
async def generate_bill(
    request: Request,
    bill_in: BillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access)
) -> Any:
    """
    Generate a bill for a shop and auto-convert to client if necessary.
    """
    service = BillingService(db)
    return await service.generate_bill_and_convert(bill_in, current_user, request)

@router.get("/", response_model=List[BillRead])
def read_bills(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access)
) -> Any:
    service = BillingService(db)
    return service.get_all_bills(skip=skip, limit=limit)

@router.get("/{bill_id}", response_model=BillRead)
def read_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_access)
) -> Any:
    service = BillingService(db)
    bill = service.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill
