from app.db import models  # noqa: F401
from app.db.database import AsyncSessionLocal, Base, engine
from app.db.models import SystemSetting
from sqlalchemy import inspect, text, select
import uuid
from sqlalchemy import inspect, text


def _ensure_user_profile_columns(sync_conn) -> None:
    inspector = inspect(sync_conn)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "address" not in columns:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN address VARCHAR(255)"))
    if "gender" not in columns:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN gender VARCHAR(20)"))
    if "birth_date" not in columns:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN birth_date DATE"))


def _ensure_payment_webhook_event_columns(sync_conn) -> None:
    inspector = inspect(sync_conn)
    if "payment_webhook_events" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("payment_webhook_events")}
    if "transaction_id" not in columns:
        sync_conn.execute(text("ALTER TABLE payment_webhook_events ADD COLUMN transaction_id VARCHAR(255)"))
    if "order_code" not in columns:
        sync_conn.execute(text("ALTER TABLE payment_webhook_events ADD COLUMN order_code VARCHAR(50)"))
    sync_conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_payment_webhook_events_transaction_id "
        "ON payment_webhook_events (transaction_id)"
    ))


async def create_missing_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_user_profile_columns)
        await conn.run_sync(_ensure_payment_webhook_event_columns)

    default_settings = {
        "sepay.enabled": (True, ["", None], "Bật/tắt SePay trong checkout"),
        "sepay.bank_code": ("TPB", ["", None, "VCB"], "Mã ngân hàng dùng để tạo VietQR"),
        "sepay.bank_name": ("TPBank", ["", None, "Vietcombank"], "Tên ngân hàng hiển thị"),
        "sepay.account_number": ("98668397979", ["", None, "0071001060528"], "Số tài khoản nhận tiền"),
        "sepay.account_name": ("THACH BAO LOC", ["", None, "CT TNHH DI VUI"], "Tên chủ tài khoản"),
        "sepay.transfer_note_prefix": ("ORDER", ["", None, "119123"], "Tiền tố nội dung chuyển khoản"),
        "sepay.qr_template": ("compact2", ["", None], "Template VietQR"),
        "sepay.webhook_url": ("https://ditravel-backend.onrender.com/api/payments/sepay/webhook", ["", None, "https://your-domain.com/api/payments/sepay/webhook"], "Webhook URL từ SePay"),
        "sepay.support_phone": ("1900 0000", ["", None], "Số hotline hỗ trợ"),
        "sepay.support_email": ("hotro@ditravel.com", ["", None], "Email hỗ trợ"),
        "sepay.description": ("Cấu hình SePay / VietQR dùng cho checkout và xác nhận thanh toán.", ["", None], "Mô tả cấu hình thanh toán"),
    }

    async with AsyncSessionLocal() as session:
        existing_result = await session.execute(
            select(SystemSetting).where(SystemSetting.key.in_(list(default_settings.keys())))
        )
        existing_map = {item.key: item for item in existing_result.scalars().all()}

        for key, (value, legacy_values, description) in default_settings.items():
            current = existing_map.get(key)
            if current is None or current.value in legacy_values:
                if current is None:
                    session.add(SystemSetting(id=uuid.uuid4(), key=key, value=value, description=description))
                else:
                    current.value = value
                    current.description = description

        await session.commit()
