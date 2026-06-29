from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import date, datetime
from typing import Optional
from app.db.models import UserType, UserStatus

# Schema chung chia sẻ các thuộc tính
class UserBase(BaseModel):
    email: EmailStr # Pydantic tự động chặn nếu không phải email thật
    full_name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None

# Schema dùng khi người dùng đăng ký/tạo tài khoản
class UserCreate(UserBase):
    password: str

# Schema dùng để kiểm tra dữ liệu trả về cho Frontend
# (Ẩn mật khẩu, chỉ trả về các trường cho phép)
class UserResponse(UserBase):
    id: UUID
    user_type: UserType
    status: UserStatus
    created_at: datetime
    
    class Config:
        from_attributes = True # Cho phép Pydantic đọc dữ liệu trực tiếp từ SQLAlchemy Model

# Schema dùng cho chức năng quên mật khẩu (chỉ cần Email)
class UserForgotPassword(BaseModel):
    email: EmailStr

# Schema dùng để đặt lại mật khẩu bằng mã OTP
class UserResetPassword(BaseModel):
    email: EmailStr
    otp_code: str
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
