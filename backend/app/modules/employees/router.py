from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker, get_current_active_user
from datetime import date as dt_date
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

@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    db.delete(employee)
    db.commit()
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)

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
        
    if user.referral_code:
        return {"employee_id": employee.id, "code": user.referral_code}

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

@router.get("/{employee_id}/id-card")
def generate_id_card(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Generate and return an ID card for the employee. Admin or Self only.
    """
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    if current_user.role != UserRole.ADMIN and current_user.id != employee.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this ID card")
    
    user = db.query(User).filter(User.id == employee.user_id).first()
    
    # Mocking ID Card generation details. In production, this would return a FileResponse of a PDF.
    return {
        "employee_id": employee.id,
        "name": user.name if hasattr(user, 'name') else "Employee Name",
        "role": user.role,
        "id_card_url": f"https://api.crm.demo/static/id_cards/emp_{employee_id}_card.pdf"
    }

from sqlalchemy import cast, Date
from app.modules.meetings.models import MeetingSummary
from app.modules.clients.models import Client

@router.get("/{pm_id}/availability")
def get_pm_availability(
    pm_id: int,
    date: dt_date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Calculate free meeting 1-hour blocks for a PM between 9 AM and 6 PM.
    """
    pm = db.query(User).filter(User.id == pm_id, User.role.in_([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])).first()
    if not pm:
         raise HTTPException(status_code=404, detail="Project Manager not found")

    meetings = db.query(MeetingSummary).join(Client).filter(
        Client.pm_id == pm_id,
        cast(MeetingSummary.date, Date) == date,
        MeetingSummary.status != "CANCELLED"
    ).all()
    
    booked_hours = [m.date.hour for m in meetings]
    
    free_slots = []
    for h in range(9, 18):
        if h not in booked_hours:
            free_slots.append(f"{h:02d}:00")
            
    return {
        "pm_id": pm_id,
        "date": date,
        "free_slots": free_slots
    }
