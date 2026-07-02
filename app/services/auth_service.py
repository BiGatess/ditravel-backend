import asyncio
import random
import secrets
import string
from datetime import datetime, timedelta
from html import escape as html_escape

import resend
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.db.models import PasswordResetToken, User


OTP_EXPIRY_SECONDS = 5 * 60
OTP_EXPIRY_LABEL = "5 phút"
RESET_TOKEN_EXPIRY_SECONDS = 10 * 60
MAX_OTP_ATTEMPTS = 5


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
        normalized_email = (email or "").strip().lower()
        query = select(User).where(func.lower(User.email) == normalized_email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    async def generate_and_send_otp(db: AsyncSession, email: str) -> bool:
        normalized_email = (email or "").strip().lower()

        query = select(User).where(func.lower(User.email) == normalized_email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return True

        otp_code = "".join(random.choices(string.digits, k=6))
        hashed_otp = get_password_hash(otp_code)
        expires_at = datetime.utcnow() + timedelta(seconds=OTP_EXPIRY_SECONDS)

        reset_entry = PasswordResetToken(
            user_id=user.id,
            email=normalized_email,
            otp_code=hashed_otp,
            expires_at=expires_at,
            attempts=0,
            is_used=False,
            reset_token=None,
            reset_token_expires_at=None,
        )
        db.add(reset_entry)
        await db.commit()

        return await AuthService._send_otp_email(normalized_email, otp_code)

    @staticmethod
    async def verify_reset_otp(db: AsyncSession, email: str, otp_code: str) -> str | None:
        normalized_email = (email or "").strip().lower()

        query = (
            select(PasswordResetToken)
            .where(
                func.lower(PasswordResetToken.email) == normalized_email,
                PasswordResetToken.is_used.is_(False),
                PasswordResetToken.expires_at > datetime.utcnow(),
            )
            .order_by(PasswordResetToken.created_at.desc())
        )
        result = await db.execute(query)
        token_row = result.scalars().first()

        if not token_row:
            return None

        attempts = token_row.attempts or 0
        if attempts >= MAX_OTP_ATTEMPTS:
            return None

        if not verify_password(otp_code, token_row.otp_code):
            token_row.attempts = attempts + 1
            await db.commit()
            return None

        reset_token = secrets.token_urlsafe(32)
        token_row.is_used = True
        token_row.reset_token = reset_token
        token_row.reset_token_expires_at = datetime.utcnow() + timedelta(seconds=RESET_TOKEN_EXPIRY_SECONDS)
        await db.commit()
        return reset_token

    @staticmethod
    async def reset_password_with_token(db: AsyncSession, reset_token: str, new_password: str) -> bool:
        token_value = (reset_token or "").strip()
        if not token_value:
            return False

        query = select(PasswordResetToken).where(
            PasswordResetToken.reset_token == token_value,
            PasswordResetToken.is_used.is_(True),
            PasswordResetToken.reset_token_expires_at > datetime.utcnow(),
        )
        result = await db.execute(query)
        token_row = result.scalars().first()

        if not token_row:
            return False

        user_query = select(User).where(User.id == token_row.user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()

        if not user:
            return False

        user.password_hash = get_password_hash(new_password)
        token_row.reset_token = None
        token_row.reset_token_expires_at = None
        await db.commit()
        return True

    @staticmethod
    async def reset_password_with_otp(db: AsyncSession, email: str, otp_code: str, new_password: str) -> bool:
        reset_token = await AuthService.verify_reset_otp(db, email=email, otp_code=otp_code)
        if not reset_token:
            return False
        return await AuthService.reset_password_with_token(db, reset_token=reset_token, new_password=new_password)

    @staticmethod
    async def _send_otp_email(to_email: str, otp_code: str) -> bool:
        if not settings.RESEND_API_KEY or not settings.EMAIL_FROM:
            return False

        def send_email_sync() -> bool:
            resend.api_key = settings.RESEND_API_KEY
            html_body = generate_forgot_password_email(to_email, otp_code)
            text_body = (
                f"Hi {to_email},\n\n"
                f"Your DI Travel verification code is: {otp_code}\n\n"
                f"This code expires after {OTP_EXPIRY_LABEL}.\n"
                "If you did not request this, you can ignore this email.\n\n"
                "No-reply: no-reply@ditravel.com\n"
                "DI Travel, Vietnam\n"
                "Copyright 2026 DI Travel. All rights reserved."
            )

            try:
                resend.Emails.send(
                    {
                        "from": settings.EMAIL_FROM,
                        "to": [to_email],
                        "subject": "Help us protect your account",
                        "html": html_body,
                        "text": text_body,
                    }
                )
                return True
            except Exception as exc:
                print(f"[mail] Failed to send email via Resend: {exc}")
                return False

        return await asyncio.to_thread(send_email_sync)
