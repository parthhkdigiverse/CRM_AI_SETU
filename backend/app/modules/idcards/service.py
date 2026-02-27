from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.modules.employees.models import Employee
from app.modules.idcards.schemas import IDCardData

class IDCardService:
    def __init__(self, db: Session):
        self.db = db

    def get_id_card_data(self, employee_id: int) -> IDCardData:
        employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        user = employee.user
        
        return IDCardData(
            employee_name=user.name or "Employee",
            employee_code=employee.employee_code,
            role=user.role.value if hasattr(user.role, 'value') else str(user.role),
            joining_date=employee.joining_date,
            photo_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={user.name or user.email}",
            qr_data=f"EMP:{employee.employee_code}|NAME:{user.name}"
        )
