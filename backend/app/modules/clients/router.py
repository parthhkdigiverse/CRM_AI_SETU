from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.clients.models import Client
from app.modules.clients.schemas import ClientCreate, ClientRead, ClientUpdate
from app.modules.clients.service import ClientService

router = APIRouter()

# Role definitions
admin_checker = RoleChecker([UserRole.ADMIN])
staff_checker = RoleChecker([
    UserRole.ADMIN, 
    UserRole.SALES, 
    UserRole.TELESALES, 
    UserRole.PROJECT_MANAGER, 
    UserRole.PROJECT_MANAGER_AND_SALES
])

@router.post("/", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(
    *,
    db: Session = Depends(get_db),
    client_in: ClientCreate,
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Create a new client. Available for all staff.
    """
    service = ClientService(db)
    # Check email uniqueness 
    if db.query(Client).filter(Client.email == client_in.email).first():
        raise HTTPException(status_code=400, detail="Client with this email already exists.")
    
    return service.create_client(client_in, current_user)

@router.get("/", response_model=List[ClientRead])
def read_clients(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Retrieve all clients with optional search and pagination.
    """
    service = ClientService(db)
    return service.get_clients(skip=skip, limit=limit, search=search, sort_by=sort_by, sort_order=sort_order)

@router.get("/{client_id}", response_model=ClientRead)
def read_client_by_id(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Get a specific client.
    """
    service = ClientService(db)
    client = service.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(
    request: Request,
    client_id: int,
    client_in: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Update a client.
    """
    service = ClientService(db)
    return await service.update_client(client_id, client_in, current_user, request)

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    request: Request,
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    """
    Delete a client. Restricted to Admins.
    """
    service = ClientService(db)
    await service.delete_client(client_id, current_user, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


