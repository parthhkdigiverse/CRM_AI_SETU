# backend/app/modules/shops/router.py
from typing import List, Any, Dict, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, status, Query, HTTPException
from pydantic import BaseModel
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.shops.schemas import ShopCreate, ShopRead, ShopUpdate, AssignPMRequest
from app.core.enums import MasterPipelineStage
from app.modules.shops.service import ShopService
from app.modules.clients.schemas import ClientRead
from app.modules.shops.models import Shop
from beanie.operators import In

class ScheduleDemoRequest(BaseModel):
    scheduled_at: datetime
    title: Optional[str] = None
    demo_type: Optional[str] = None
    notes: Optional[str] = None

router = APIRouter()

# Staff can read and write Shops
staff_checker = RoleChecker([
    UserRole.ADMIN,
    UserRole.SALES,
    UserRole.TELESALES,
    UserRole.PROJECT_MANAGER,
    UserRole.PROJECT_MANAGER_AND_SALES
])

admin_checker = RoleChecker([UserRole.ADMIN])

pm_checker = RoleChecker([
    UserRole.ADMIN,
    UserRole.PROJECT_MANAGER,
    UserRole.PROJECT_MANAGER_AND_SALES
])

@router.post("/", response_model=ShopRead, status_code=status.HTTP_201_CREATED)
async def create_shop(
    shop_in: ShopCreate,
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.create_shop(shop_in, current_user)

@router.get("/kanban", response_model=Dict[str, List[ShopRead]])
async def read_kanban_shops(
    my_view: bool = Query(False, description="If true, only return leads assigned to the current user"),
    owner_id: Optional[int] = Query(None),
    source: Optional[str] = Query(None),
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    effective_owner_id = owner_id
    if (current_user and current_user.role in {UserRole.SALES, UserRole.TELESALES}) or my_view:
        effective_owner_id = current_user.id if current_user else 0
    return await service.list_kanban_shops(owner_id=effective_owner_id, source=source)

@router.get("/archived", response_model=List[ShopRead])
async def read_archived_shops(
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.get_archived_shops(current_user)

@router.get("/demo-queue", response_model=List[ShopRead])
async def read_demo_queue(
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.get_demo_queue(current_user)

@router.get("/", response_model=List[ShopRead])
async def read_shops(
    skip: int = 0,
    limit: int = 100,
    pipeline_stage: Optional[MasterPipelineStage] = None,
    owner_id: Optional[int] = None,
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.list_shops(current_user, skip, limit, pipeline_stage, owner_id)

@router.get("/suggest-pm")
async def suggest_pm(
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.suggest_least_busy_pm(current_user)

@router.get("/analytics/pm-pipeline")
async def read_pm_pipeline_analytics(
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.get_pm_pipeline_analytics()

@router.get("/{shop_id}", response_model=ShopRead)
async def read_shop(
    shop_id: str,
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.get_shop(shop_id)

@router.patch("/{shop_id}", response_model=ShopRead)
async def update_shop(
    shop_id: str,
    shop_in: ShopUpdate,
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.update_shop(shop_id, shop_in)

@router.post("/{shop_id}/accept", response_model=ShopRead)
async def accept_shop(
    shop_id: str,
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.accept_shop(shop_id, current_user)

@router.post("/{shop_id}/assign-pm", response_model=ShopRead)
async def assign_pm(
    shop_id: str,
    body: AssignPMRequest,
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.assign_pm(shop_id, body.pm_id, current_user)

@router.post("/{shop_id}/auto-assign", response_model=ShopRead)
async def auto_assign_shop(
    shop_id: str,
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.auto_assign_shop(shop_id, current_user)

@router.post("/{shop_id}/schedule-demo", response_model=ShopRead)
async def schedule_demo(
    shop_id: str,
    body: ScheduleDemoRequest,
    current_user: User = Depends(pm_checker)
) -> Any:
    service = ShopService()
    return await service.schedule_demo(shop_id, body, current_user)

@router.post("/{shop_id}/complete-demo", response_model=ShopRead)
async def complete_demo(
    shop_id: str,
    current_user: User = Depends(pm_checker)
) -> Any:
    service = ShopService()
    return await service.complete_demo(shop_id, current_user)

@router.post("/{shop_id}/cancel-demo", response_model=ShopRead)
async def cancel_demo(
    shop_id: str,
    current_user: User = Depends(pm_checker)
) -> Any:
    service = ShopService()
    return await service.cancel_demo(shop_id, current_user)

@router.post("/{shop_id}/approve", response_model=ClientRead)
async def approve_pipeline(
    shop_id: str,
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.approve_pipeline_entry(shop_id)

@router.delete("/{shop_id}", status_code=status.HTTP_200_OK)
async def archive_shop(
    shop_id: str,
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.archive_shop(shop_id, current_user)

@router.patch("/{shop_id}/unarchive", response_model=ShopRead)
async def unarchive_shop(
    shop_id: str,
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.unarchive_shop(shop_id, current_user)

@router.delete("/{shop_id}/hard-delete", status_code=status.HTTP_200_OK)
async def hard_delete_shop(
    shop_id: str,
    current_user: User = Depends(admin_checker)
) -> Any:
    service = ShopService()
    return await service.hard_delete_shop(shop_id)

@router.post("/batch-delete")
async def batch_delete_shops(
    ids: List[int],
    current_user: User = Depends(admin_checker)
):
    try:
        shops = await Shop.find(In(Shop.id, ids)).to_list()
        for shop in shops:
            await shop.delete()
        return {"message": f"Successfully deleted {len(ids)} leads"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/accepted/history")
async def read_accepted_leads_history(
    current_user: User = Depends(staff_checker)
) -> Any:
    service = ShopService()
    return await service.get_accepted_leads(current_user)
