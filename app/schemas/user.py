from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import date, datetime
from typing import Optional
from app.db.models import UserType, UserStatus


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: UUID
    user_type: UserType
    status: UserStatus
    created_at: datetime

    class Config:
        from_attributes = True


class UserForgotPassword(BaseModel):
    email: EmailStr


class UserVerifyResetOtp(BaseModel):
    email: EmailStr
    otp_code: str


class UserResetPassword(BaseModel):
    reset_token: str
    new_password: str


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None


class UserChangePassword(BaseModel):
    current_password: str
    new_password: str
