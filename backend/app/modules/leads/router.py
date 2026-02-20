from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.leads.schemas import LeadCreate, LeadRead, LeadUpdate
from app.modules.clients.schemas import ClientRead
from app.modules.leads.service import LeadService

router = APIRouter()

# Role Definitions
sales_access = RoleChecker([UserRole.SALES, UserRole.TELESALES, UserRole.ADMIN])
# Only Sales and Admin can convert (assumption from plan, verifying against user request)
# User request: "Convert shop -> client: Sales, Admin"
# Create shop/lead: "Sales, Telesales"
create_access = RoleChecker([UserRole.SALES, UserRole.TELESALES])
convert_access = RoleChecker([UserRole.SALES, UserRole.ADMIN])

@router.post("/", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(
    request: Request,
    lead_in: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(create_access)
) -> Any:
    """
    Create a new Lead (Shop).
    Allowed: Sales, Telesales.
    """
    service = LeadService(db)
    return await service.create_lead(lead_in, current_user, request)

@router.get("/", response_model=List[LeadRead])
def read_leads(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(sales_access) # View access for all sales/admin
) -> Any:
    service = LeadService(db)
    # If Telesales, maybe only see own? enforcing basic list for now
    return service.get_leads(skip, limit)

@router.get("/{lead_id}", response_model=LeadRead)
def read_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(sales_access)
) -> Any:
    service = LeadService(db)
    lead = service.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.post("/{lead_id}/convert", response_model=ClientRead)
async def convert_lead(
    request: Request,
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(convert_access)
) -> Any:
    """
    Convert Lead to Client.
    Allowed: Sales, Admin.
    """
    service = LeadService(db)
    return await service.convert_lead(lead_id, current_user, request)

@router.patch("/{lead_id}", response_model=LeadRead)
async def update_lead(
    request: Request,
    lead_id: int,
    lead_in: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(create_access) # Same as create
) -> Any:
    service = LeadService(db)
    return await service.update_lead(lead_id, lead_in, current_user, request)
