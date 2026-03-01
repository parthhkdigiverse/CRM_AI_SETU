from sqlalchemy import Column, Integer, String, ForeignKey, Date, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    employee_code = Column(String, unique=True, index=True, nullable=False)
    joining_date = Column(Date, nullable=False)
    base_salary = Column(Float, default=0.0)
    target = Column(Integer, default=0)
    department = Column(String, nullable=True)

    user = relationship("User", backref="employee_profile")
    leaves = relationship("LeaveRecord", back_populates="employee")

# Import related models for relationships
from app.modules.users.models import User
from app.modules.salary.models import LeaveRecord
