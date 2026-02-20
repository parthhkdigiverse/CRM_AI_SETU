from sqlalchemy.orm import Session
from app.modules.employees.models import Employee
from app.modules.employees.schemas import EmployeeCreate, EmployeeUpdate
from app.modules.users.models import User
from fastapi import HTTPException

class EmployeeService:
    @staticmethod
    def create_employee(db: Session, employee_in: EmployeeCreate) -> Employee:
        # Business logic validation
        user = db.query(User).filter(User.id == employee_in.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        existing = db.query(Employee).filter(Employee.user_id == employee_in.user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Employee profile already exists for this user")

        db_employee = Employee(**employee_in.model_dump())
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)
        return db_employee

    @staticmethod
    def get_employee(db: Session, employee_id: int) -> Employee:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        return employee

    @staticmethod
    def list_employees(db: Session, skip: int = 0, limit: int = 100):
        return db.query(Employee).offset(skip).limit(limit).all()

    @staticmethod
    def update_employee(db: Session, employee_id: int, employee_in: EmployeeUpdate) -> Employee:
        db_employee = EmployeeService.get_employee(db, employee_id)
        update_data = employee_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_employee, field, value)
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)
        return db_employee
