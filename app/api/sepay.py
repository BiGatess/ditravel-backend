import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.db.database import get_db
from app.db.models import PaymentWebhookEvent, SystemSetting, User

router = APIRouter()


async def _get_setting_value(db: AsyncSession, key: str) -> Any:
    result = await db.execute(select(SystemSetting.value).where(SystemSetting.key == key))
    return result.scalar_one_or_none()


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, (int, float)):
        # Heuristic: assume milliseconds if the timestamp is large.
        if value > 10_000_000_000:
            value = value / 1000
        return datetime.fromtimestamp(value, tz=timezone.utc)

    if isinstance(value, str):
        candidates = [
            value,
            value.replace("Z", "+00:00"),
        ]
        for candidate in candidates:
            try:
                parsed = datetime.fromisoformat(candidate)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

    return None


def _extract_first(payload: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def _build_reference_code(payload: dict[str, Any]) -> str:
    reference = _extract_first(
        payload,
        [
            "transaction_id",
            "transactionId",
            "id",
            "code",
            "reference_code",
            "referenceCode",
            "bank_transaction_id",
            "bankTransactionId",
        ],
    )
    if reference:
        return str(reference)

    normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@router.post("/webhook")
async def sepay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_sepay_secret: str | None = Header(default=None, alias="X-SePay-Secret"),
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
    x_signature: str | None = Header(default=None, alias="X-Signature"),
):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook payload must be a JSON object")

    configured_secret = await _get_setting_value(db, "sepay.webhook_secret")
    if configured_secret:
        request_secrets = {
            str(x_sepay_secret or "").strip(),
            str(x_webhook_secret or "").strip(),
            str(x_signature or "").strip(),
            str(payload.get("secret") or "").strip(),
            str(payload.get("webhook_secret") or "").strip(),
        }
        if str(configured_secret).strip() not in request_secrets:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")

    reference_code = _build_reference_code(payload)
    amount = _to_decimal(
        _extract_first(
            payload,
            ["amount", "transfer_amount", "transferAmount", "creditAmount", "paid_amount", "value"],
        )
    )
    content = _extract_first(
        payload,
        ["content", "description", "transfer_content", "transferContent", "memo", "addInfo", "message"],
    )
    bank_code = _extract_first(payload, ["bank_code", "bankCode", "bank", "bank_short_name"])
    account_number = _extract_first(payload, ["account_number", "accountNumber", "accountNo", "account"])
    account_name = _extract_first(payload, ["account_name", "accountName", "account_holder_name", "accountHolderName"])
    status_value = str(_extract_first(payload, ["status", "state", "transaction_status"]) or "SUCCESS").upper()
    transaction_time = _parse_datetime(
        _extract_first(
            payload,
            ["transaction_time", "transactionTime", "trans_time", "transTime", "created_at", "createdAt", "time"],
        )
    )

    result = await db.execute(
        select(PaymentWebhookEvent).where(PaymentWebhookEvent.reference_code == reference_code)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.amount = amount
        existing.content = content
        existing.bank_code = bank_code
        existing.account_number = account_number
        existing.account_name = account_name
        existing.status = status_value
        existing.transaction_time = transaction_time
        existing.raw_payload = payload
        await db.commit()
        await db.refresh(existing)
        return {"ok": True, "duplicate": True, "reference_code": existing.reference_code}

    event = PaymentWebhookEvent(
        reference_code=reference_code,
        provider="SEPAY",
        amount=amount,
        content=content,
        bank_code=bank_code,
        account_number=account_number,
        account_name=account_name,
        status=status_value,
        transaction_time=transaction_time,
        raw_payload=payload,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    return {"ok": True, "duplicate": False, "reference_code": event.reference_code}


@router.get("/revenue")
async def sepay_revenue_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(
            func.count(PaymentWebhookEvent.id),
            func.coalesce(func.sum(PaymentWebhookEvent.amount), 0),
            func.max(PaymentWebhookEvent.transaction_time),
        ).where(PaymentWebhookEvent.status == "SUCCESS")
    )
    success_count, total_amount, latest_transaction_time = result.one()

    latest_event_result = await db.execute(
        select(PaymentWebhookEvent).order_by(desc(PaymentWebhookEvent.created_at)).limit(5)
    )
    latest_events = latest_event_result.scalars().all()

    return {
        "success_count": int(success_count or 0),
        "total_amount": str(total_amount or 0),
        "latest_transaction_time": latest_transaction_time,
        "latest_events": [
            {
                "reference_code": event.reference_code,
                "amount": str(event.amount or 0),
                "content": event.content,
                "bank_code": event.bank_code,
                "account_number": event.account_number,
                "account_name": event.account_name,
                "status": event.status,
                "transaction_time": event.transaction_time,
                "created_at": event.created_at,
            }
            for event in latest_events
        ],
    }
