import enum
from sqlalchemy import Column, Integer, String, Enum, Boolean
from app.core.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    SALES = "SALES"
    TELESALES = "TELESALES"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    PROJECT_MANAGER_AND_SALES = "PROJECT_MANAGER_AND_SALES"
    CLIENT = "CLIENT"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.TELESALES, nullable=False)
    is_active = Column(Boolean, default=True)
