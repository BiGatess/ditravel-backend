from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.security import create_access_token
from app.schemas.token import Token
from app.schemas.user import UserForgotPassword, UserResetPassword, UserCreate, UserResponse
from app.services.auth_service import AuthService
from app.api.deps import get_current_user
from app.db.models import User
from app.core.config import settings

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Đăng ký tài khoản mới (dùng để test). 
    Trong thực tế, bạn có thể thiết lập tài khoản đăng ký mặc định là ADMIN.
    """
    from app.db.models import User, UserType
    from sqlalchemy.future import select
    from app.core.security import get_password_hash
    
    # Kiểm tra email trùng
    query = select(User).where(User.email == data.email)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email này đã được đăng ký")
        
    new_user = User(
        email=data.email,
        full_name=data.full_name,
        phone=data.phone,
        password_hash=get_password_hash(data.password),
        user_type=UserType.USER
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Đăng nhập bằng Email và Password
    Nếu thành công trả về JWT Token.
    (Chú ý: form_data.username ở đây chính là Email do frontend gửi)
    """
    user = await AuthService.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản hoặc mật khẩu không chính xác",
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Lấy thông tin tài khoản hiện tại thông qua Token"""
    return current_user


@router.post("/forgot-password")
async def forgot_password(
    data: UserForgotPassword,
    db: AsyncSession = Depends(get_db)
):
    """
    Khởi tạo quá trình quên mật khẩu.
    Hệ thống sẽ tạo mã OTP 6 số, lưu vào Redis 90s và gửi qua Email.
    """
    success = await AuthService.generate_and_send_otp(db, email=data.email)
    
    # Dù tài khoản có tồn tại hay không, vẫn trả về thông báo chung chung
    # để chống hacker dò tìm xem email nào đã đăng ký
    return {"message": "Nếu email hợp lệ, mã OTP đã được gửi. Vui lòng kiểm tra hộp thư."}


@router.post("/reset-password")
async def reset_password(
    data: UserResetPassword,
    db: AsyncSession = Depends(get_db)
):
    """
    Xác nhận mã OTP để đổi mật khẩu mới
    """
    success = await AuthService.reset_password_with_otp(
        db, email=data.email, otp_code=data.otp_code, new_password=data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không chính xác hoặc đã hết hạn (quá 90 giây)"
        )
        
    return {"message": "Đổi mật khẩu thành công!"}
