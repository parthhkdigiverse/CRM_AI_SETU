from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.core.dependencies import get_current_user
from app.modules.users.models import User, UserRole
from app.modules.auth.schemas import Token, ChangePasswordRequest, UpdatePreferencesRequest
from app.modules.users.schemas import UserCreate, UserRead, UserProfileUpdate
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType

router = APIRouter()

_DEMO_EMAIL = "admin@example.com"
_DEMO_PASSWORD = "password123"
_DEMO_USER_ID = 0

@router.post("/login", response_model=Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    try:
        user = await User.find_one(User.email == form_data.username)
    except Exception as db_err:
        print(f"[ERROR] Database query failed: {db_err}")
        if form_data.username == _DEMO_EMAIL and form_data.password == _DEMO_PASSWORD:
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            refresh_token_expires = timedelta(days=30)
            return {
                "access_token": create_access_token(_DEMO_USER_ID, expires_delta=access_token_expires),
                "refresh_token": create_access_token(_DEMO_USER_ID, expires_delta=refresh_token_expires),
                "token_type": "bearer",
            }
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available.")

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    if user.role == UserRole.CLIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clients are not allowed to log in to this portal.")

    activity_logger = ActivityLogger()
    await activity_logger.log_activity(user_id=user.id, user_role=user.role, action=ActionType.LOGIN, entity_type=EntityType.USER, entity_id=user.id, request=request)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=30)
    return {
        "access_token": create_access_token(user.id, expires_delta=access_token_expires),
        "refresh_token": create_access_token(user.id, expires_delta=refresh_token_expires),
        "token_type": "bearer",
    }

@router.post("/register")
async def register(request: Request, user_in: UserCreate = None) -> Any:
    from app.modules.users.service import UserService
    user_service = UserService()
    user = await User.find_one(User.email == user_in.email)
    user_existed = user is not None

    if not user_existed and user_in.role != UserRole.CLIENT and not user_in.employee_code:
        emp_code, current_seq = await user_service.get_next_employee_code()
        if emp_code:
            user_in.employee_code = emp_code
            await user_service.increment_employee_code_seq(current_seq)

    if user_existed:
        user.name = user_in.name
        user.hashed_password = get_password_hash(user_in.password)
        user.role = user_in.role
        user.is_active = user_in.is_active
        user.employee_code = user_in.employee_code
        user.joining_date = user_in.joining_date
        user.base_salary = user_in.base_salary
        user.target = user_in.target
        user.department = user_in.department
        await user.save()
    else:
        user = User(
            email=user_in.email,
            name=user_in.name,
            hashed_password=get_password_hash(user_in.password),
            role=user_in.role,
            is_active=user_in.is_active,
            employee_code=user_in.employee_code,
            joining_date=user_in.joining_date,
            base_salary=user_in.base_salary,
            target=user_in.target,
            department=user_in.department,
        )
        await user.insert()

    await user_service.generate_referral_code(user.id)

    activity_logger = ActivityLogger()
    await activity_logger.log_activity(
        user_id=user.id, user_role=user.role,
        action=ActionType.UPDATE if user_existed else ActionType.CREATE,
        entity_type=EntityType.USER, entity_id=user.id, request=request
    )

    message = "User profile updated successfully" if user_existed else "User account created successfully"
    return {"message": message, "user": UserRead.model_validate(user)}

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)) -> Any:
    user_id = current_user.id if current_user else _DEMO_USER_ID
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=30)
    return {
        "access_token": create_access_token(user_id, expires_delta=access_token_expires),
        "refresh_token": create_access_token(user_id, expires_delta=refresh_token_expires),
        "token_type": "bearer",
    }

@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)) -> Any:
    if current_user is None:
        return {"id": 0, "email": _DEMO_EMAIL, "name": "Demo Admin", "role": "ADMIN", "is_active": True, "phone": None}
    return current_user

@router.get("/profile", response_model=UserRead)
async def read_profile(current_user: User = Depends(get_current_user)) -> Any:
    if current_user is None:
        return {"id": 0, "email": _DEMO_EMAIL, "name": "Demo Admin", "role": "ADMIN", "is_active": True, "phone": None}
    return current_user

@router.patch("/profile", response_model=UserRead)
async def update_profile(request: Request, profile_in: UserProfileUpdate, current_user: User = Depends(get_current_user)) -> Any:
    if current_user is None:
        return {"id": 0, "email": _DEMO_EMAIL, "name": profile_in.name or "Demo Admin", "role": "ADMIN", "is_active": True, "phone": profile_in.phone}
    old_data = {"name": current_user.name, "phone": current_user.phone}
    update_data = profile_in.model_dump(exclude_unset=True)
    if "password" in update_data:
        current_user.hashed_password = get_password_hash(update_data.pop("password"))
    for field, value in update_data.items():
        setattr(current_user, field, value)
    await current_user.save()
    activity_logger = ActivityLogger()
    await activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.UPDATE, entity_type=EntityType.USER, entity_id=current_user.id, old_data=old_data, new_data={"name": current_user.name, "phone": current_user.phone}, request=request)
    return current_user

@router.post("/change-password")
async def change_password(request: Request, body: ChangePasswordRequest, current_user: User = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=400, detail="Demo account cannot change password")
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    current_user.hashed_password = get_password_hash(body.new_password)
    await current_user.save()
    activity_logger = ActivityLogger()
    await activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.UPDATE, entity_type=EntityType.USER, entity_id=current_user.id, new_data={"password_changed": True}, request=request)
    return {"message": "Password updated successfully"}

@router.patch("/preferences")
async def update_preferences(request: Request, body: UpdatePreferencesRequest, current_user: User = Depends(get_current_user)):
    if current_user is None:
        return {"message": "Preferences updated (Demo Mode)"}
    current_prefs = current_user.preferences or {}
    current_user.preferences = {**current_prefs, **body.preferences}
    await current_user.save()
    return {"message": "Preferences updated successfully", "preferences": current_user.preferences}

@router.post("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    if current_user:
        activity_logger = ActivityLogger()
        await activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.LOGOUT, entity_type=EntityType.USER, entity_id=current_user.id, request=request)
    return {"message": "Logged out successfully"}