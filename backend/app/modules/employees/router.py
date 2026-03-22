from datetime import date as dt_date
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from app.core.dependencies import RoleChecker, get_current_active_user
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserRead, UserCreate, EmployeeUpdate

router = APIRouter()

admin_checker = RoleChecker([UserRole.ADMIN])

@router.get("/", response_model=List[UserRead])
async def list_employees(limit: Optional[int] = Query(None), department: Optional[str] = Query(None), role: Optional[UserRole] = Query(None), is_active: Optional[bool] = Query(None), start_date: Optional[dt_date] = Query(None), end_date: Optional[dt_date] = Query(None), current_user: User = Depends(get_current_active_user)) -> Any:
    if current_user.role != UserRole.ADMIN:
        return [current_user]
    query_filter = [User.is_deleted != True]
    if department:
        query_filter.append(User.department == department)
    if role:
        query_filter.append(User.role == role)
    if is_active is not None:
        query_filter.append(User.is_active == is_active)
    if start_date:
        query_filter.append(User.joining_date >= start_date)
    if end_date:
        query_filter.append(User.joining_date <= end_date)
    users = await User.find(*query_filter).to_list()
    if limit:
        users = users[:limit]
    return users

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_employee(employee_in: UserCreate, current_user: User = Depends(admin_checker)) -> Any:
    existing = await User.find_one(User.email == employee_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    from app.core.security import get_password_hash
    user = User(email=employee_in.email, hashed_password=get_password_hash(employee_in.password), name=employee_in.name, phone=employee_in.phone, role=employee_in.role, is_active=employee_in.is_active if employee_in.is_active is not None else True, employee_code=employee_in.employee_code, joining_date=employee_in.joining_date, base_salary=employee_in.base_salary, target=employee_in.target, department=employee_in.department)
    await user.insert()
    return user

@router.patch("/{employee_id}", response_model=UserRead)
async def update_employee(employee_id: int, update_in: EmployeeUpdate, current_user: User = Depends(admin_checker)) -> Any:
    user = await User.find_one(User.id == employee_id, User.is_deleted != True)
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
    await user.save()
    return user

@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(employee_id: int, current_user: User = Depends(admin_checker)):
    user = await User.find_one(User.id == employee_id, User.is_deleted != True)
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
    user.is_deleted = True
    await user.save()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
