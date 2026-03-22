import jwt
from typing import Optional, Any, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.modules.users.models import User, UserRole
from app.modules.auth.schemas import TokenData

# Beanie/MongoDB ma get_db ni jarur nathi, etle tya thi kashu import nahi karvanu
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> Optional[User]:
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

    # Demo mode check
    if token_data.sub == "0":
        return None

    try:
        # Beanie (MongoDB) ma sidhu Model.get() vapray che
        user = await User.get(token_data.sub)
    except Exception as e:
        print(f"DATABASE ERROR in get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error. Check your MongoDB Atlas config.",
        )
        
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Optional[User] = Depends(get_current_user),
) -> Optional[User]:
    if current_user is None:  # Demo Mode (Synthetic User)
        return None
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

class RoleChecker:
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    async def __call__(self, user: Optional[User] = Depends(get_current_active_user)):
        # Synthetic User handling for Demo Admin
        if user is None:
            class SyntheticUser:
                id = "0"
                email = "admin@example.com"
                name = "Demo Admin"
                role = UserRole.ADMIN
                is_active = True
                def __getitem__(self, key):
                    return getattr(self, key)
            
            # Jo ADMIN allowed hoy to j SyntheticUser return karvo
            if UserRole.ADMIN in self.allowed_roles:
                return SyntheticUser()
            else:
                raise HTTPException(status_code=403, detail="Not enough privileges")

        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return user