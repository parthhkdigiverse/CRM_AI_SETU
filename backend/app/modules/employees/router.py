from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.employees.models import Employee
from app.modules.employees.schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate

from app.modules.employees.service import EmployeeService

router = APIRouter()

# Only Admins can manage employee profiles
admin_checker = RoleChecker([UserRole.ADMIN])

@router.post("/", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    *,
    db: Session = Depends(get_db),
    employee_in: EmployeeCreate,
    current_user: User = Depends(admin_checker)
) -> Any:
    return EmployeeService.create_employee(db, employee_in)

@router.get("/", response_model=List[EmployeeRead])
def read_employees(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_checker)
) -> Any:
    return EmployeeService.list_employees(db, skip, limit)

@router.get("/{employee_id}", response_model=EmployeeRead)
def read_employee_by_id(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    return EmployeeService.get_employee(db, employee_id)

@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    employee_in: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    return EmployeeService.update_employee(db, employee_id, employee_in)

# Referral Code Management
from app.modules.employees.schemas import ReferralCodeCreate, ReferralCodeRead
import uuid

@router.post("/{employee_id}/referral-code", response_model=ReferralCodeRead)
def generate_referral_code(
    employee_id: int,
    referral_in: ReferralCodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker) # Or allowed roles
) -> Any:
    employee = EmployeeService.get_employee(db, employee_id)
    if not employee:
         raise HTTPException(status_code=404, detail="Employee not found")
    
    user = db.query(User).filter(User.id == employee.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User associated with employee not found")

    allowed_roles = [UserRole.SALES, UserRole.TELESALES]
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=400, 
            detail=f"Referral codes can only be generated for roles: {allowed_roles}"
        )

    code = referral_in.code
    if not code:
        # Generate unique code: REF-{Initials}-{Random}
        # For simplicity: REF-{user_id}-{uuid}
        code = f"REF-{user.id}-{str(uuid.uuid4())[:8].upper()}"
    
    # Check uniqueness
    existing = db.query(User).filter(User.referral_code == code).first()
    if existing and existing.id != user.id:
        raise HTTPException(status_code=400, detail="Referral code already exists")

    user.referral_code = code
    db.commit()
    db.refresh(user)
    
    return {"employee_id": employee.id, "code": user.referral_code}

@router.get("/{employee_id}/referral-code", response_model=ReferralCodeRead)
def get_referral_code(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
) -> Any:
    employee = EmployeeService.get_employee(db, employee_id)
    if not employee:
         raise HTTPException(status_code=404, detail="Employee not found")
    
    user = db.query(User).filter(User.id == employee.user_id).first()
    if not user.referral_code:
        raise HTTPException(status_code=404, detail="Referral code not set for this employee")
        
    return {"employee_id": employee.id, "code": user.referral_code}

    return {"employee_id": employee.id, "code": user.referral_code}
