"""
Employees router — thin alias over /users/ for backward-compatibility.
The 'employees' concept was merged into 'users'; this router keeps the
/employees/* endpoints alive so the frontend doesn't 404.
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import RoleChecker, get_current_active_user
from app.modules.users.models import User, UserRole
<<<<<<< HEAD
from app.modules.users.schemas import UserRead, UserCreate, UserProfileUpdate
=======
from app.modules.users.schemas import UserRead, UserCreate, EmployeeUpdate
>>>>>>> 4e9077c30962ca43722946a88198cd1531425287

router = APIRouter()

admin_checker = RoleChecker([UserRole.ADMIN])


@router.get("/", response_model=List[UserRead])
def list_employees(
    limit: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """List all non-deleted users (employees). Accessible to all authenticated users."""
    q = db.query(User).filter(User.is_deleted == False)
    if limit:
        q = q.limit(limit)
    return q.all()


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    employee_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker),
) -> Any:
    """Create a new user/employee (Admin only)."""
    existing = db.query(User).filter(User.email == employee_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    from app.core.security import get_password_hash
    hashed = get_password_hash(employee_in.password)

    user = User(
        email=employee_in.email,
        hashed_password=hashed,
        name=employee_in.name,
        phone=employee_in.phone,
        role=employee_in.role,
        is_active=employee_in.is_active if employee_in.is_active is not None else True,
        employee_code=employee_in.employee_code,
        joining_date=employee_in.joining_date,
        base_salary=employee_in.base_salary,
        target=employee_in.target,
        department=employee_in.department,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{employee_id}", response_model=UserRead)
def update_employee(
    employee_id: int,
<<<<<<< HEAD
    update_in: UserProfileUpdate,
=======
    update_in: EmployeeUpdate,
>>>>>>> 4e9077c30962ca43722946a88198cd1531425287
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker),
) -> Any:
    """Update a user/employee profile (Admin only)."""
    user = db.query(User).filter(User.id == employee_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")

    update_data = update_in.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        from app.core.security import get_password_hash
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    else:
        update_data.pop("password", None)

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker),
):
    """Soft-delete a user/employee (Admin only)."""
    user = db.query(User).filter(User.id == employee_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")

    user.is_deleted = True
    db.commit()

    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)
