from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.core.dependencies import get_current_user
from app.modules.users.models import User, UserRole
from app.modules.auth.schemas import Token
from app.modules.users.schemas import UserCreate, UserRead, UserProfileUpdate
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from fastapi import Request

router = APIRouter()

# ──────────────────────────────────────────────────────────────────────────────
# DEMO / FALLBACK account — used when the database is not yet configured.
# Anyone who clones the repo and hasn't set up PostgreSQL can still log in.
#   Email:    admin@example.com
#   Password: password123
# ──────────────────────────────────────────────────────────────────────────────
_DEMO_EMAIL    = "admin@example.com"
_DEMO_PASSWORD = "password123"
_DEMO_USER_ID  = 0  # Synthetic ID — not a real DB row

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    # ── Try the real database first ───────────────────────────────────────────
    try:
        user = db.query(User).filter(User.email == form_data.username).first()
    except (OperationalError, Exception) as db_err:
        # ── Database is not reachable — check demo credentials ────────────────
        print(f"[DEMO MODE] Database unavailable ({db_err.__class__.__name__}). "
              f"Checking fallback demo credentials...")
        if (
            form_data.username == _DEMO_EMAIL
            and form_data.password == _DEMO_PASSWORD
        ):
            print("[DEMO MODE] Demo login granted for admin@example.com")
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            refresh_token_expires = timedelta(days=30)
            return {
                "access_token": create_access_token(
                    _DEMO_USER_ID, expires_delta=access_token_expires
                ),
                "refresh_token": create_access_token(
                    _DEMO_USER_ID, expires_delta=refresh_token_expires
                ),
                "token_type": "bearer",
            }
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available. Please set up your .env and run database migrations. "
                   "You can use admin@example.com / password123 as demo credentials.",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    is_password_correct = verify_password(form_data.password, user.hashed_password)

    if not is_password_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    if user.role == UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clients are not allowed to log in to this portal.",
        )
    
    # Log Login
    activity_logger = ActivityLogger(db)
    await activity_logger.log_activity(
        user_id=user.id,
        user_role=user.role,
        action=ActionType.LOGIN,
        entity_type=EntityType.USER,
        entity_id=user.id,
        request=request
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=30)
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "refresh_token": create_access_token(
            user.id, expires_delta=refresh_token_expires
        ),
        "token_type": "bearer",
    }

@router.post("/register", response_model=UserRead)
async def register(
    request: Request,
    db: Session = Depends(get_db),
    user_in: UserCreate = None
) -> Any:
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
        is_active=user_in.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Log Registration
    activity_logger = ActivityLogger(db)
    await activity_logger.log_activity(
        user_id=user.id,
        user_role=user.role,
        action=ActionType.CREATE,
        entity_type=EntityType.USER,
        entity_id=user.id,
        request=request
    )

    return user

@router.post("/refresh", response_model=Token)
def refresh_token(
    current_user: User = Depends(get_current_user),
) -> Any:
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=30)
    return {
        "access_token": create_access_token(
            current_user.id, expires_delta=access_token_expires
        ),
        "refresh_token": create_access_token(
            current_user.id, expires_delta=refresh_token_expires
        ),
        "token_type": "bearer",
    }

@router.get("/me", response_model=UserRead)
def read_current_user(
    current_user: User = Depends(get_current_user)
) -> Any:
    if current_user is None:  # Demo mode: return synthetic admin
        return {
            "id": 0, "email": _DEMO_EMAIL, "name": "Demo Admin",
            "role": "ADMIN", "is_active": True, "phone": None
        }
    return current_user

@router.get("/profile", response_model=UserRead)
def read_profile(current_user: User = Depends(get_current_user)) -> Any:
    if current_user is None:  # Demo mode: return synthetic admin
        return {
            "id": 0, "email": _DEMO_EMAIL, "name": "Demo Admin",
            "role": "ADMIN", "is_active": True, "phone": None
        }
    return current_user

@router.patch("/profile", response_model=UserRead)
async def update_profile(
    request: Request,
    profile_in: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    old_data = {"name": current_user.name, "phone": current_user.phone}
    update_data = profile_in.model_dump(exclude_unset=True)
    
    if "password" in update_data:
        current_user.hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        
    for field, value in update_data.items():
        setattr(current_user, field, value)
        
    db.commit()
    db.refresh(current_user)
    
    activity_logger = ActivityLogger(db)
    await activity_logger.log_activity(
        user_id=current_user.id,
        user_role=current_user.role,
        action=ActionType.UPDATE,
        entity_type=EntityType.USER,
        entity_id=current_user.id,
        old_data=old_data,
        new_data={"name": current_user.name, "phone": current_user.phone},
        request=request
    )
    return current_user

@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    activity_logger = ActivityLogger(db)
    await activity_logger.log_activity(
        user_id=current_user.id,
        user_role=current_user.role,
        action=ActionType.LOGOUT,
        entity_type=EntityType.USER,
        entity_id=current_user.id,
        request=request
    )
    return {"message": "Logged out successfully"}
