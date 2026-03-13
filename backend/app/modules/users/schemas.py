from typing import Optional, Any
from datetime import date
from pydantic import BaseModel, EmailStr, field_validator
from app.modules.users.models import UserRole

class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = UserRole.TELESALES
    is_active: Optional[bool] = True
    incentive_enabled: Optional[bool] = True

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.upper()
        return v

class UserCreate(UserBase):
    email: EmailStr
    name: str
    password: str
    # Optional employee/HR fields (filled by Admin at creation time)
    employee_code: Optional[str] = None
    joining_date: Optional[date] = None
    base_salary: Optional[float] = None
    target: Optional[int] = None
    department: Optional[str] = None

    @field_validator("email")
    @classmethod
    def check_email_deliverability(cls, v: str) -> str:
        from email_validator import validate_email, EmailNotValidError
        try:
            # check_deliverability=True performs a DNS MX record check
            validate_email(v, check_deliverability=True)
            return v
        except EmailNotValidError as e:
            raise ValueError(f"Invalid or non-existent email domain: {str(e)}")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    preferences: Optional[dict] = None
    # Admin-editable employee fields
    employee_code: Optional[str] = None
    joining_date: Optional[date] = None
    base_salary: Optional[float] = None
    target: Optional[int] = None
    incentive_enabled: Optional[bool] = None
    department: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password_profile(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

class EmployeeUpdate(UserProfileUpdate):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class UserRead(UserBase):
    id: int
    employee_code: Optional[str] = None
    joining_date: Optional[date] = None
    base_salary: Optional[float] = None
    target: Optional[int] = None
    department: Optional[str] = None
    referral_code: Optional[str] = None
    preferences: Optional[dict] = None

    class Config:
        from_attributes = True

