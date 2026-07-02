import asyncio
from html import escape as html_escape

try:
    import resend
except ModuleNotFoundError:  # pragma: no cover - optional dependency in some environments
    resend = None
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.db.database import get_db
from app.db.models import SystemSetting
from app.schemas.contact import ContactRequest, ContactResponse

router = APIRouter()


def _strip_address(value: str | None) -> str | None:
    if not value:
        return None
    if "<" in value and ">" in value:
        return value.split("<", 1)[1].split(">", 1)[0].strip()
    return value.strip()


async def _get_support_email(db: AsyncSession) -> str | None:
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == "sepay.support_email"))
    setting = result.scalar_one_or_none()
    configured_email = setting.value if setting and isinstance(setting.value, str) else None
    return _strip_address(configured_email or settings.ADMIN_EMAIL or settings.EMAIL_FROM)


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_contact_request(data: ContactRequest, db: AsyncSession = Depends(get_db)):
    if resend is None or not settings.RESEND_API_KEY or not settings.EMAIL_FROM:
        raise HTTPException(status_code=503, detail="Chưa cấu hình email gửi hỗ trợ trên server.")

    support_email = await _get_support_email(db)
    if not support_email:
        raise HTTPException(status_code=503, detail="Chưa cấu hình email nhận hỗ trợ.")

    safe_name = html_escape(data.name.strip())
    safe_phone = html_escape((data.phone or "").strip() or "Không cung cấp")
    safe_email = html_escape(str(data.email or "").strip() or "Không cung cấp")
    safe_subject = html_escape(data.subject.strip())
    safe_order_id = html_escape((data.order_id or "").strip() or "Không có")
    safe_message = html_escape(data.message.strip()).replace("\n", "<br/>")

    html_body = f"""
    <div style="font-family:Arial,Helvetica,sans-serif;color:#111827;line-height:1.6">
      <h2>Yêu cầu hỗ trợ mới từ DiTravel</h2>
      <p><strong>Họ tên:</strong> {safe_name}</p>
      <p><strong>Số điện thoại:</strong> {safe_phone}</p>
      <p><strong>Email:</strong> {safe_email}</p>
      <p><strong>Chủ đề:</strong> {safe_subject}</p>
      <p><strong>Mã đơn hàng:</strong> {safe_order_id}</p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0" />
      <p><strong>Nội dung:</strong></p>
      <p>{safe_message}</p>
    </div>
    """
    text_body = (
        "Yêu cầu hỗ trợ mới từ DiTravel\n\n"
        f"Họ tên: {data.name.strip()}\n"
        f"Số điện thoại: {(data.phone or '').strip() or 'Không cung cấp'}\n"
        f"Email: {str(data.email or '').strip() or 'Không cung cấp'}\n"
        f"Chủ đề: {data.subject.strip()}\n"
        f"Mã đơn hàng: {(data.order_id or '').strip() or 'Không có'}\n\n"
        f"Nội dung:\n{data.message.strip()}\n"
    )

    email_payload = {
        "from": settings.EMAIL_FROM,
        "to": [support_email],
        "subject": f"[DiTravel] {data.subject.strip()}",
        "html": html_body,
        "text": text_body,
    }
    if data.email:
        email_payload["reply_to"] = str(data.email)

    def send_email_sync() -> None:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send(email_payload)

    try:
        await asyncio.to_thread(send_email_sync)
    except Exception as exc:
        print(f"[contact] Failed to send support email: {exc}")
        raise HTTPException(status_code=502, detail="Không gửi được yêu cầu hỗ trợ. Vui lòng thử lại sau.")

    return {"message": "Yêu cầu hỗ trợ đã được gửi."}
