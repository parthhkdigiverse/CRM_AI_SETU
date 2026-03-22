from beanie import Document, Indexed
from pydantic import EmailStr
from typing import Optional, Dict, Any
from datetime import date
import enum

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    SALES = "SALES"
    TELESALES = "TELESALES"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    PROJECT_MANAGER_AND_SALES = "PROJECT_MANAGER_AND_SALES"
    CLIENT = "CLIENT"

class User(Document):
    email: Indexed(str, unique=True)
    hashed_password: str
    name: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole = UserRole.TELESALES
    referral_code: Optional[str] = None
    is_active: bool = True
    is_deleted: bool = False
    preferences: Optional[Dict[str, Any]] = {}
    employee_code: Optional[str] = None
    joining_date: Optional[date] = None
    base_salary: float = 0.0
    target: int = 0
    incentive_enabled: bool = True
    department: Optional[str] = None

    class Settings:
        name = "users"
