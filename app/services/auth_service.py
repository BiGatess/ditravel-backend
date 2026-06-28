import random
import string
import asyncio
import time
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import User, PasswordResetToken
from app.core.security import verify_password, get_password_hash
from app.core.config import settings

# --- MÔ PHỎNG REDIS CHO MÔI TRƯỜNG CODE ---
# Vì máy bạn chưa cài phần mềm Redis thật, tôi sẽ dùng bộ nhớ tạm của Python 
# để mô phỏng y hệt tính năng tự huỷ sau 90 giây của Redis để bạn test.
# Khi nào deploy lên máy chủ thật, mình sẽ bật kết nối Redis lại!
class MockRedis:
    def __init__(self):
        self.data = {}
    
    async def setex(self, key, seconds, value):
        expire_at = time.time() + seconds
        self.data[key] = {"value": value, "expire_at": expire_at}
        
    async def get(self, key):
        if key in self.data:
            if time.time() > self.data[key]["expire_at"]:
                del self.data[key] # Đã hết hạn thì xoá
                return None
            return self.data[key]["value"]
        return None
        
    async def delete(self, key):
        if key in self.data:
            del self.data[key]

redis_client = MockRedis()
# ------------------------------------------

class AuthService:
    
    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
        """Kiểm tra đăng nhập"""
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    async def generate_and_send_otp(db: AsyncSession, email: str) -> bool:
        """Tạo mã OTP, lưu vào Redis 90s và gửi Email"""
        # 1. Tìm user
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return False # Không báo lỗi rõ ràng để chống hacker dò email
            
        # 2. Tạo mã OTP 6 số ngẫu nhiên
        otp_code = ''.join(random.choices(string.digits, k=6))
        
        # 3. Lưu vào Redis với hạn 90 GIÂY
        redis_key = f"reset_otp:{email}"
        await redis_client.setex(redis_key, 90, otp_code)
        
        # 4. Lưu log vào Database (để đối soát nếu cần)
        hashed_otp = get_password_hash(otp_code)
        expires_at = datetime.utcnow() + timedelta(seconds=90)
        reset_token = PasswordResetToken(
            user_id=user.id,
            email=email,
            otp_code=hashed_otp,
            expires_at=expires_at
        )
        db.add(reset_token)
        await db.commit()
        
        # 5. Gửi Email (Chạy nền không làm chậm API)
        asyncio.create_task(AuthService._send_email_async(email, otp_code))
        
        return True

    @staticmethod
    async def reset_password_with_otp(db: AsyncSession, email: str, otp_code: str, new_password: str) -> bool:
        """Kiểm tra OTP và Đổi mật khẩu"""
        # 1. Kiểm tra OTP trên Redis (90s)
        redis_key = f"reset_otp:{email}"
        saved_otp = await redis_client.get(redis_key)
        
        if not saved_otp or saved_otp != otp_code:
            return False # Mã sai hoặc đã hết hạn (bị xoá khỏi Redis)
            
        # 2. OTP đúng, tiến hành đổi mật khẩu
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            user.password_hash = get_password_hash(new_password)
            # Cập nhật db log (is_used = True)
            token_query = select(PasswordResetToken).where(
                PasswordResetToken.email == email,
                PasswordResetToken.is_used == False
            ).order_by(PasswordResetToken.created_at.desc())
            token_result = await db.execute(token_query)
            token_log = token_result.scalars().first()
            if token_log:
                token_log.is_used = True
            
            await db.commit()
            
            # Xoá mã OTP khỏi Redis ngay lập tức (không cho dùng lại)
            await redis_client.delete(redis_key)
            return True
            
        return False

    @staticmethod
    async def _send_email_async(to_email: str, otp_code: str):
        """Hàm gửi Email thật bằng Gmail SMTP (chạy trên thread riêng để không block API)"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        def send_email_sync():
            # Nếu chưa cấu hình email trong .env thì vẫn in ra Terminal như cũ
            if not settings.SMTP_EMAIL or not settings.SMTP_PASSWORD:
                print("==================================================")
                print(f"📧 CHƯA CÓ EMAIL TRONG .ENV. ĐANG IN GIẢ LẬP GỬI ĐẾN: {to_email}")
                print(f"🔑 MÃ OTP CỦA BẠN LÀ: {otp_code}")
                print(f"⏳ Cảnh báo: Mã sẽ tự huỷ sau 90 giây!")
                print("==================================================")
                return

            msg = MIMEMultipart()
            # Đổi tên người gửi hiển thị ở đây (VD: DiTravel Support)
            msg['From'] = f"Hỗ trợ DiTravel <{settings.SMTP_EMAIL}>"
            msg['To'] = to_email
            msg['Subject'] = "Mã xác nhận quên mật khẩu - DiTravel"
            
            body = f"Xin chào,\n\nMã OTP của bạn là: {otp_code}.\n\nMã này sẽ tự động hết hạn sau 90 giây.\nVui lòng không chia sẻ mã này cho bất kỳ ai.\n\nTrân trọng,\nĐội ngũ DiTravel."
            msg.attach(MIMEText(body, 'plain'))
            
            try:
                # Kết nối máy chủ Gmail
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
                server.send_message(msg)
                server.quit()
                print(f"✅ Đã gửi email OTP thành công tới: {to_email}")
            except Exception as e:
                print(f"❌ Lỗi gửi email: {e}")

        # Chạy hàm đồng bộ trên một thread riêng để không làm treo hệ thống Async
        await asyncio.to_thread(send_email_sync)
