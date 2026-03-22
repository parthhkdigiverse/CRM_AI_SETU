from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.clients.models import Client
from app.modules.clients.schemas import ClientCreate, ClientRead, ClientUpdate, ClientPMAssign, PMWorkloadRead, ClientPMHistoryRead
from app.modules.clients.service import ClientService

router = APIRouter()

admin_checker = RoleChecker([UserRole.ADMIN])
staff_checker = RoleChecker([UserRole.ADMIN, UserRole.SALES, UserRole.TELESALES, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])

@router.post("/", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
async def create_client(client_in: ClientCreate, request: Request, current_user: User = Depends(staff_checker)) -> Any:
    service = ClientService()
    if client_in.email:
        existing = await Client.find_one(Client.email == client_in.email)
        if existing:
            raise HTTPException(status_code=400, detail="Client with this email already exists.")
    return await service.create_client(client_in, current_user, request)

@router.get("/", response_model=List[ClientRead])
async def read_clients(skip: int = 0, limit: int = 100, search: Optional[str] = None, status: Optional[str] = None, pm_id: Optional[str] = None, sort_by: Optional[str] = "created_at", sort_order: Optional[str] = "desc", current_user: User = Depends(staff_checker)) -> Any:
    service = ClientService()
    resolved_pm_id = None
    owner_id = None
    scoped_user_id = None
    scoped_mode = None
    client_active_status: Optional[bool] = True
    normalized_status = (status or "").strip().lower()
    if normalized_status in {"inactive", "false"}:
        client_active_status = False
    elif normalized_status == "all":
        client_active_status = None
    if current_user and current_user.role != UserRole.ADMIN:
        if current_user.role == UserRole.PROJECT_MANAGER:
            scoped_user_id = current_user.id
            scoped_mode = "pm"
        elif current_user.role == UserRole.PROJECT_MANAGER_AND_SALES:
            scoped_user_id = current_user.id
            scoped_mode = "mixed"
        elif current_user.role in [UserRole.SALES, UserRole.TELESALES]:
            scoped_user_id = current_user.id
            scoped_mode = "owner"
    elif pm_id and pm_id not in {"ALL", "all"}:
        try:
            resolved_pm_id = int(pm_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid pm_id")
    return await service.get_clients(skip=skip, limit=limit, search=search, sort_by=sort_by, sort_order=sort_order, pm_id=resolved_pm_id, owner_id=owner_id, is_active=client_active_status, scoped_user_id=scoped_user_id, scoped_mode=scoped_mode)

@router.get("/my-clients", response_model=List[ClientRead])
async def read_my_clients(skip: int = 0, limit: int = 100, search: Optional[str] = None, sort_by: Optional[str] = "created_at", sort_order: Optional[str] = "desc", current_user: User = Depends(RoleChecker([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]))) -> Any:
    service = ClientService()
    return await service.get_clients(skip=skip, limit=limit, search=search, sort_by=sort_by, sort_order=sort_order, pm_id=current_user.id)

@router.get("/pm-workload", response_model=List[PMWorkloadRead])
async def get_pm_workload(current_user: User = Depends(admin_checker)) -> Any:
    service = ClientService()
    return await service.get_pm_workload()

@router.post("/retroactive-balance", status_code=status.HTTP_200_OK)
async def retroactive_balance_clients(current_user: User = Depends(admin_checker)) -> Any:
    service = ClientService()
    return await service.retroactive_pm_balance()

@router.get("/{client_id}", response_model=ClientRead)
async def read_client_by_id(client_id: str, current_user: User = Depends(staff_checker)) -> Any:
    service = ClientService()
    client = await service.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role != UserRole.ADMIN:
        has_access = (client.owner_id == current_user.id or client.pm_id == current_user.id or client.referred_by_id == current_user.id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")
    return client

@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(request: Request, client_id: str, client_in: ClientUpdate, current_user: User = Depends(staff_checker)) -> Any:
    service = ClientService()
    return await service.update_client(client_id, client_in, current_user, request)

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(request: Request, client_id: str, current_user: User = Depends(admin_checker)):
    service = ClientService()
    await service.delete_client(client_id, current_user, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{client_id}/assign-pm", response_model=ClientRead)
async def assign_pm(request: Request, client_id: str, assign_in: ClientPMAssign, current_user: User = Depends(admin_checker)) -> Any:
    service = ClientService()
    return await service.assign_pm(client_id, assign_in.pm_id, current_user, request)

@router.get("/{client_id}/pm-history", response_model=List[ClientPMHistoryRead])
async def get_client_pm_history(client_id: str, current_user: User = Depends(staff_checker)) -> Any:
    service = ClientService()
    client = await service.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return await service.get_pm_history(client_id)
