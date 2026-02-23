from typing import List, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.shops.schemas import ShopCreate, ShopRead, ShopUpdate
from app.modules.shops.service import ShopService

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

@router.get("/", response_model=List[ShopRead])
def read_shops(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(staff_checker)
) -> Any:
    return ShopService.list_shops(db, skip, limit)

@router.get("/{shop_id}", response_model=ShopRead)
def read_shop(
    shop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    return ShopService.get_shop(db, shop_id)

@router.patch("/{shop_id}", response_model=ShopRead)
def update_shop(
    shop_id: int,
    shop_in: ShopUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    return ShopService.update_shop(db, shop_id, shop_in)

@router.delete("/{shop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shop(
    shop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    ShopService.delete_shop(db, shop_id)
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)
