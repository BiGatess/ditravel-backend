from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.database import get_db
from app.db.models import User
from app.schemas.token import Token
from app.schemas.user import (
    UserChangePassword,
    UserCreate,
    UserForgotPassword,
    UserProfileUpdate,
    UserResetPassword,
    UserResponse,
    UserVerifyResetOtp,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    from app.db.models import User, UserStatus, UserType

    query = select(User).where(User.email == data.email)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email này đã được đăng ký")

    new_user = User(
        email=data.email,
        full_name=data.full_name,
        phone=data.phone,
        password_hash=get_password_hash(data.password),
        user_type=UserType.USER,
        status=UserStatus.ACTIVE,
    )

    try:
        db.add(new_user)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Email này đã được đăng ký")

    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = await AuthService.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản hoặc mật khẩu không chính xác",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(subject=user.id, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_users_me(
    data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payload = data.model_dump(exclude_unset=True)

    if "full_name" in payload:
        full_name = (payload["full_name"] or "").strip()
        if not full_name:
            raise HTTPException(status_code=400, detail="Vui lòng nhập họ và tên")
        current_user.full_name = full_name

    if "email" in payload and payload["email"]:
        email = str(payload["email"]).strip().lower()
        if email != current_user.email:
            result = await db.execute(select(User).where(User.email == email, User.id != current_user.id))
            if result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Email này đã được sử dụng")
        current_user.email = email

    if "phone" in payload:
        phone = (payload["phone"] or "").strip()
        current_user.phone = phone or None

    if "address" in payload:
        address = (payload["address"] or "").strip()
        current_user.address = address or None

    if "gender" in payload:
        gender = (payload["gender"] or "").strip()
        if gender and gender not in {"male", "female", "other"}:
            raise HTTPException(status_code=400, detail="Giới tính không hợp lệ")
        current_user.gender = gender or None

    if "birth_date" in payload:
        current_user.birth_date = payload["birth_date"]

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Email này đã được sử dụng")

    await db.refresh(current_user)
    return current_user


@router.post("/change-password")
async def change_password(
    data: UserChangePassword,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải có ít nhất 6 ký tự")

    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không chính xác")

    current_user.password_hash = get_password_hash(data.new_password)
    await db.commit()

    return {"message": "Đổi mật khẩu thành công"}


@router.post("/forgot-password")
async def forgot_password(data: UserForgotPassword, db: AsyncSession = Depends(get_db)):
    success = await AuthService.generate_and_send_otp(db, email=data.email)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không gửi được email OTP. Kiểm tra SMTP_EMAIL / SMTP_PASSWORD trên Render hoặc email người dùng.",
        )
    return {"message": "Nếu email hợp lệ, mã OTP đã được gửi. Vui lòng kiểm tra hộp thư."}


@router.post("/verify-reset-otp")
async def verify_reset_otp(data: UserVerifyResetOtp, db: AsyncSession = Depends(get_db)):
    reset_token = await AuthService.verify_reset_otp(db, email=data.email, otp_code=data.otp_code)
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không chính xác hoặc đã hết hạn (60 giây).",
        )

    return {
        "message": "OTP hợp lệ. Bạn có thể nhập mật khẩu mới.",
        "reset_token": reset_token,
    }


@router.post("/reset-password")
async def reset_password(data: UserResetPassword, db: AsyncSession = Depends(get_db)):
    if data.reset_token:
        success = await AuthService.reset_password_with_token(
            db, reset_token=data.reset_token, new_password=data.new_password
        )
    elif data.email and data.otp_code:
        success = await AuthService.reset_password_with_otp(
            db, email=data.email, otp_code=data.otp_code, new_password=data.new_password
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu thông tin xác minh để đổi mật khẩu.",
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không chính xác hoặc đã hết hạn (60 giây).",
        )

    return {"message": "Đổi mật khẩu thành công!"}
