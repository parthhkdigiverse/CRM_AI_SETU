from typing import List, Any, Dict
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.shops.schemas import ShopCreate, ShopRead, ShopUpdate, ShopStatus
from app.modules.shops.service import ShopService
from app.modules.clients.schemas import ClientRead

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

@router.post("/", response_model=ShopRead, status_code=status.HTTP_201_CREATED)
def create_shop(
    *,
    db: Session = Depends(get_db),
    shop_in: ShopCreate,
    current_user: User = Depends(staff_checker)
) -> Any:
    return ShopService.create_shop(db, shop_in)

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

@router.get("/", response_model=List[ShopRead])
def read_shops(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: ShopStatus = None,
    owner_id: int = None,
    current_user: User = Depends(staff_checker)
) -> Any:
    return ShopService.list_shops(db, skip, limit, status, owner_id)

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

@router.post("/{shop_id}/approve", response_model=ClientRead)
def approve_pipeline(
    shop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    return ShopService.approve_pipeline_entry(db, shop_id)

@router.delete("/{shop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shop(
    shop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    ShopService.delete_shop(db, shop_id)
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)

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
