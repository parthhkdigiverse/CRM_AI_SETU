# backend/app/core/dependencies.py
import jwt
from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.modules.users.models import User, UserRole
from app.modules.auth.schemas import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class SyntheticUser:
    """A mock user for Demo or Dev modes."""
    id = 0
    email = "admin@example.com"
    name = "Demo Admin"
    role = UserRole.ADMIN
    is_active = True
    preferences = {}
    hashed_password = "hashed_password_placeholder"
    
    def __getitem__(self, key):
        return getattr(self, key)

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    if token == "dev-token":
        # Bypass JWT validation for frontend dev mode (Admin mockup)
        return SyntheticUser()

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(sub=user_id)
    except jwt.PyJWTError:
        raise credentials_exception
    # Demo mode: synthetic admin — skip DB lookup
    user_id_int = int(token_data.sub)
    if user_id_int == 0:
        return SyntheticUser()

    from sqlalchemy.exc import OperationalError
    try:
        user = db.query(User).filter(User.id == user_id_int).first()
    except OperationalError as db_err:
        import traceback
        print(f"DATABASE ERROR in get_current_user: {db_err}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available. Please configure your .env and run migrations.",
        )
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user is None:
        return None
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

class RoleChecker:
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_active_user)):
        if user is None:
            return SyntheticUser()

        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return user
