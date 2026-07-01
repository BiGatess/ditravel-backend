import asyncio
import json
import random
import secrets
import string
import time
from datetime import datetime, timedelta
from html import escape as html_escape

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.db.models import PasswordResetToken, User


class MockRedis:
    def __init__(self):
        self.data = {}

    async def setex(self, key, seconds, value):
        expire_at = time.time() + seconds
        self.data[key] = {"value": value, "expire_at": expire_at}

    async def get(self, key):
        if key in self.data:
            if time.time() > self.data[key]["expire_at"]:
                del self.data[key]
                return None
            return self.data[key]["value"]
        return None

    async def delete(self, key):
        if key in self.data:
            del self.data[key]


redis_client = MockRedis()

OTP_EXPIRY_SECONDS = 60
OTP_EXPIRY_LABEL = "60 giây"
RESET_SESSION_EXPIRY_SECONDS = 10 * 60


def generate_forgot_password_email(userEmail: str, otpCode: str) -> str:
    safe_email = html_escape(userEmail or "")
    safe_otp = html_escape(otpCode or "")

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Help us protect your account</title>
  </head>
  <body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,Helvetica,sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f5f5f5;padding:40px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:480px;background:#ffffff;border-radius:12px;overflow:hidden;">
            <tr>
              <td style="padding:40px 36px 28px 36px;">
                <div style="text-align:center;">
                  <h1 style="margin:0;font-size:26px;line-height:1.3;font-weight:700;color:#111827;">
                    Help us protect your account
                  </h1>
                  <div style="width:88px;height:3px;background:#8e44dd;margin:14px auto 0;border-radius:999px;"></div>
                </div>

                <p style="margin:28px 0 0 0;font-size:15px;line-height:1.7;color:#374151;">
                  Hi <strong style="color:#111827;">{safe_email}</strong>,
                </p>

                <p style="margin:14px 0 0 0;font-size:15px;line-height:1.7;color:#374151;">
                  We received a request to reset your password for your DI Travel account.
                  Use the verification code below to continue:
                </p>

                <div style="margin:28px 0 24px 0;padding:18px 16px;background:#8e44dd;border-radius:12px;text-align:center;">
                  <div style="font-size:12px;line-height:1.4;color:rgba(255,255,255,0.85);text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-bottom:10px;">
                    Your OTP Code
                  </div>
                  <div style="font-size:34px;line-height:1.2;font-weight:800;letter-spacing:8px;color:#ffffff;font-family:Arial,Helvetica,sans-serif;">
                    {safe_otp}
                  </div>
                </div>

                <p style="margin:0;font-size:14px;line-height:1.7;color:#6b7280;">
                  This code will expire after <strong style="color:#111827;">{OTP_EXPIRY_LABEL}</strong>.
                </p>

                <p style="margin:10px 0 0 0;font-size:14px;line-height:1.7;color:#6b7280;">
                  If you did not request this change, you can safely ignore this email.
                </p>
              </td>
            </tr>

            <tr>
              <td style="padding:18px 36px 30px 36px;border-top:1px solid #ececec;background:#ffffff;">
                <p style="margin:0;font-size:12px;line-height:1.6;color:#9ca3af;text-align:center;">
                  No-reply: no-reply@ditravel.com<br />
                  DI Travel, Vietnam<br />
                  Copyright 2026 DI Travel. All rights reserved.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def generateForgotPasswordEmail(userEmail: str, otpCode: str) -> str:
    return generate_forgot_password_email(userEmail, otpCode)


class AuthService:
    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
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
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return False

        otp_code = "".join(random.choices(string.digits, k=6))

        redis_key = f"reset_otp:{email}"
        await redis_client.setex(redis_key, OTP_EXPIRY_SECONDS, otp_code)

        hashed_otp = get_password_hash(otp_code)
        expires_at = datetime.utcnow() + timedelta(seconds=OTP_EXPIRY_SECONDS)
        reset_token = PasswordResetToken(
            user_id=user.id,
            email=email,
            otp_code=hashed_otp,
            expires_at=expires_at,
        )
        db.add(reset_token)
        await db.commit()

        asyncio.create_task(AuthService._send_email_async(email, otp_code))
        return True

    @staticmethod
    async def verify_reset_otp(db: AsyncSession, email: str, otp_code: str) -> str | None:
        redis_key = f"reset_otp:{email}"
        saved_otp = await redis_client.get(redis_key)

        if not saved_otp or saved_otp != otp_code:
            return None

        reset_token = secrets.token_urlsafe(32)
        session_key = f"reset_session:{reset_token}"
        session_value = json.dumps(
            {
                "email": email,
                "verified_at": datetime.utcnow().isoformat(),
            }
        )
        await redis_client.setex(session_key, RESET_SESSION_EXPIRY_SECONDS, session_value)
        return reset_token

    @staticmethod
    async def reset_password_with_token(db: AsyncSession, reset_token: str, new_password: str) -> bool:
        session_key = f"reset_session:{reset_token}"
        session_data = await redis_client.get(session_key)

        if not session_data:
            return False

        try:
            payload = json.loads(session_data)
        except (TypeError, json.JSONDecodeError):
            return False

        email = payload.get("email")
        if not email:
            return False

        query = select(User).where(User.email == email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if user:
            user.password_hash = get_password_hash(new_password)

            token_query = select(PasswordResetToken).where(
                PasswordResetToken.email == email,
                PasswordResetToken.is_used.is_(False),
            ).order_by(PasswordResetToken.created_at.desc())
            token_result = await db.execute(token_query)
            token_log = token_result.scalars().first()
            if token_log:
                token_log.is_used = True

            await db.commit()
            await redis_client.delete(f"reset_otp:{email}")
            await redis_client.delete(session_key)
            return True

        return False

    @staticmethod
    async def reset_password_with_otp(db: AsyncSession, email: str, otp_code: str, new_password: str) -> bool:
        reset_token = await AuthService.verify_reset_otp(db, email=email, otp_code=otp_code)
        if not reset_token:
            return False
        return await AuthService.reset_password_with_token(db, reset_token=reset_token, new_password=new_password)

    @staticmethod
    async def _send_email_async(to_email: str, otp_code: str):
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        def send_email_sync():
            if not settings.SMTP_EMAIL or not settings.SMTP_PASSWORD:
                print("==================================================")
                print(f"[mail] SMTP not configured. Mock send to: {to_email}")
                print(f"[mail] OTP: {otp_code}")
                print(f"[mail] Code expires after {OTP_EXPIRY_LABEL}")
                print("==================================================")
                return

            msg = MIMEMultipart("alternative")
            msg["From"] = f"DiTravel Support <{settings.SMTP_EMAIL}>"
            msg["To"] = to_email
            msg["Subject"] = "Help us protect your account"

            text_body = (
                f"Hi {to_email},\n\n"
                f"Your DI Travel verification code is: {otp_code}\n\n"
                f"This code expires after {OTP_EXPIRY_LABEL}.\n"
                "If you did not request this, you can ignore this email.\n\n"
                "No-reply: no-reply@ditravel.com\n"
                "DI Travel, Vietnam\n"
                "Copyright 2026 DI Travel. All rights reserved."
            )
            html_body = generate_forgot_password_email(to_email, otp_code)

            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            try:
                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
                server.send_message(msg)
                server.quit()
                print(f"[mail] OTP email sent successfully to: {to_email}")
            except Exception as e:
                print(f"[mail] Failed to send email: {e}")

        await asyncio.to_thread(send_email_sync)
