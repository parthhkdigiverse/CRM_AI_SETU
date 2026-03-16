# backend/app/modules/shops/router.py
from typing import List, Any, Dict, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, status, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.shops.schemas import ShopCreate, ShopRead, ShopUpdate, ShopStatus, AssignPMRequest
from app.modules.shops.service import ShopService
from app.modules.clients.schemas import ClientRead

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
def create_shop(
    *,
    db: Session = Depends(get_db),
    shop_in: ShopCreate,
    current_user: User = Depends(staff_checker)
) -> Any:
    return ShopService.create_shop(db, shop_in, current_user)

@router.get("/kanban", response_model=Dict[str, List[ShopRead]])
def read_kanban_shops(
    db: Session = Depends(get_db),
    my_view: bool = Query(False, description="If true, only return leads assigned to the current user"),
    owner_id: int | None = Query(None),
    source: str | None = Query(None),
    current_user: User = Depends(staff_checker)
) -> Any:
    # Automatically scope to current user if they are a sales/telesales employee (not admin/PM)
    employee_roles = {UserRole.SALES, UserRole.TELESALES}
    effective_owner_id = owner_id
    if (current_user and current_user.role in employee_roles) or my_view:
        effective_owner_id = current_user.id if current_user else 0
    return ShopService.list_kanban_shops(db, owner_id=effective_owner_id, source=source)

@router.get("/archived", response_model=List[ShopRead])
def read_archived_shops(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Get all archived shops. Staff scope limited by permissions.
    """
    return ShopService.get_archived_shops(db, current_user)

@router.get("/demo-queue", response_model=List[ShopRead])
def read_demo_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Get all shops in the PM demo queue. PMs see only their own; Admins see all.
    """
    return ShopService.get_demo_queue(db, current_user)

@router.get("/", response_model=List[ShopRead])
def read_shops(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: ShopStatus = None,
    owner_id: int = None,
    current_user: User = Depends(staff_checker)
) -> Any:
    return ShopService.list_shops(db, current_user, skip, limit, status, owner_id)

@router.get("/suggest-pm")
def suggest_pm(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Suggest a Project Manager with the lowest workload.
    """
    return ShopService.suggest_least_busy_pm(db, current_user)

@router.get("/{shop_id}", response_model=ShopRead)
def read_shop(
    shop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    shop = ShopService.get_shop(db, shop_id)
    # Add owner_name for response model
    owner_name = db.query(User.name).filter(User.id == shop.owner_id).scalar() if shop.owner_id else None
    shop_data = shop.__dict__.copy()
    shop_data["owner_name"] = owner_name
    return shop_data

@router.patch("/{shop_id}", response_model=ShopRead)
def update_shop(
    shop_id: int,
    shop_in: ShopUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    return ShopService.update_shop(db, shop_id, shop_in)

@router.post("/{shop_id}/accept", response_model=ShopRead)
def accept_shop(
    shop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Accept a shop assignment.
    """
    return ShopService.accept_shop(db, shop_id, current_user)

@router.post("/{shop_id}/assign-pm", response_model=ShopRead)
def assign_pm(
    shop_id: int,
    body: AssignPMRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Assign a Project Manager to a CONTACTED lead.
    """
    return ShopService.assign_pm(db, shop_id, body.pm_id, current_user)

@router.post("/{shop_id}/auto-assign", response_model=ShopRead)
def auto_assign_shop(
    shop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Auto assign a Project Manager to a shop based on workload.
    """
    return ShopService.auto_assign_shop(db, shop_id, current_user)

@router.post("/{shop_id}/schedule-demo", response_model=ShopRead)
def schedule_demo(
    shop_id: int,
    body: ScheduleDemoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_checker)
) -> Any:
    """
    Schedule the next demo for a shop. Sets demo_scheduled_at.
    """
    return ShopService.schedule_demo(db, shop_id, body, current_user)

@router.post("/{shop_id}/complete-demo", response_model=ShopRead)
def complete_demo(
    shop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_checker)
) -> Any:
    """
    Mark the current demo as completed. Increments demo_stage, clears demo_scheduled_at.
    First completion (demo_stage == 1) auto-advances status to MEETING_SET.
    """
    return ShopService.complete_demo(db, shop_id, current_user)

@router.post("/{shop_id}/cancel-demo", response_model=ShopRead)
def cancel_demo(
    shop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_checker)
) -> Any:
    """
    Cancel the currently scheduled demo for a shop.
    """
    return ShopService.cancel_demo(db, shop_id, current_user)

@router.post("/{shop_id}/approve", response_model=ClientRead)
def approve_pipeline(
    shop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    return ShopService.approve_pipeline_entry(db, shop_id)

@router.delete("/{shop_id}", status_code=status.HTTP_200_OK)
def archive_shop(
    shop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Soft-delete (archive) a shop. Available to staff.
    """
    return ShopService.archive_shop(db, shop_id, current_user)

@router.patch("/{shop_id}/unarchive", response_model=ShopRead)
def unarchive_shop(
    shop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Unarchive a shop. Staff scope limited to owners/assignees.
    """
    shop = ShopService.unarchive_shop(db, shop_id, current_user)
    return shop

@router.delete("/{shop_id}/hard-delete", status_code=status.HTTP_200_OK)
def hard_delete_shop(
    shop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    """
    Permanently delete a shop. Admin only.
    """
    return ShopService.hard_delete_shop(db, shop_id)

@router.post("/batch-delete")
def batch_delete_shops(
    ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    from app.modules.shops.models import Shop
    try:
        db.query(Shop).filter(Shop.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        return {"message": f"Successfully deleted {len(ids)} leads"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/accepted/history")
def read_accepted_leads_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Get history of accepted leads. Scoped by role.
    """
    return ShopService.get_accepted_leads(db, current_user)

@router.get("/analytics/pm-pipeline")
def read_pm_pipeline_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Get pipeline status counts grouped by PM.
    """
    return ShopService.get_pm_pipeline_analytics(db)
