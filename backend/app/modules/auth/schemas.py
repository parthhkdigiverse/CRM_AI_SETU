# backend/app/modules/auth/schemas.py
from typing import Optional
from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    sub: Optional[str] = None

class LoginRequest(BaseModel):
    username: EmailStr
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class UpdatePreferencesRequest(BaseModel):
    preferences: dict
