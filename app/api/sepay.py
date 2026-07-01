import hashlib
import hmac
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.config import settings
from app.core.currency import normalize_vnd_price
from app.db.database import get_db
from app.db.models import Order, OrderStatus, PaymentStatus, PaymentWebhookEvent, SystemSetting, User

router = APIRouter()


async def _get_setting_value(db: AsyncSession, key: str) -> Any:
    result = await db.execute(select(SystemSetting.value).where(SystemSetting.key == key))
    return result.scalar_one_or_none()


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        normalized = normalize_vnd_price(value)
        return Decimal(str(normalized)) if normalized is not None else None
    except Exception:
        return None


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, (int, float)):
        if value > 10_000_000_000:
            value = value / 1000
        return datetime.fromtimestamp(value, tz=timezone.utc)

    if isinstance(value, str):
        candidates = [value, value.replace("Z", "+00:00")]
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


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _build_reference_code(payload: dict[str, Any]) -> str:
    reference = _extract_first(
        payload,
        [
            "reference_code",
            "referenceCode",
            "reference",
            "ref_code",
            "refCode",
            "code",
            "transaction_reference",
            "transactionReference",
        ],
    )
    if reference:
        return _normalize_text(reference)

    transaction_id = _extract_first(
        payload,
        [
            "transaction_id",
            "transactionId",
            "id",
            "bank_transaction_id",
            "bankTransactionId",
        ],
    )
    if transaction_id:
        return _normalize_text(transaction_id)

    normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _build_transaction_id(payload: dict[str, Any]) -> Optional[str]:
    transaction_id = _extract_first(
        payload,
        [
            "transaction_id",
            "transactionId",
            "id",
            "bank_transaction_id",
            "bankTransactionId",
            "bank_txn_id",
            "bankTxnId",
        ],
    )
    return _normalize_text(transaction_id) if transaction_id else None


def _extract_order_code(payload: dict[str, Any]) -> Optional[str]:
    direct = _extract_first(
        payload,
        [
            "order_code",
            "orderCode",
            "payment_code",
            "paymentCode",
            "reference_order_code",
            "referenceOrderCode",
        ],
    )
    if direct:
        normalized = _normalize_text(direct).upper().replace(" ", "")
        match = re.search(r"ORDER\d+", normalized)
        return match.group(0) if match else normalized

    text_candidates = [
        _extract_first(payload, ["content", "description", "transfer_content", "transferContent", "memo", "addInfo", "message"]),
        _extract_first(payload, ["note", "remark"]),
    ]
    for value in text_candidates:
        if not value:
            continue
        normalized = _normalize_text(value).upper().replace(" ", "")
        match = re.search(r"ORDER\d+", normalized)
        if match:
            return match.group(0)
    return None


def _hmac_matches(secret: str, body: bytes, signatures: list[str]) -> bool:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    candidates = {digest.lower(), f"sha256={digest.lower()}"}
    for signature in signatures:
        normalized = signature.strip().lower()
        if not normalized:
            continue
        for candidate in candidates:
            if hmac.compare_digest(normalized, candidate):
                return True
    return False


async def _find_order_by_code(db: AsyncSession, order_code: Optional[str]) -> Optional[Order]:
    if not order_code:
        return None
    result = await db.execute(select(Order).where(Order.order_code == order_code))
    return result.scalar_one_or_none()


@router.post("/webhook")
async def sepay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_sepay_secret: str | None = Header(default=None, alias="X-SePay-Secret"),
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    x_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
):
    body = await request.body()
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook payload must be a JSON object")

    configured_secret = _normalize_text(settings.SEPAY_WEBHOOK_SECRET or await _get_setting_value(db, "sepay.webhook_secret"))
    if configured_secret:
        header_signatures = [
            _normalize_text(x_sepay_secret),
            _normalize_text(x_webhook_secret),
            _normalize_text(x_signature),
            _normalize_text(x_signature_256),
            _normalize_text(payload.get("secret")),
            _normalize_text(payload.get("webhook_secret")),
        ]
        if not _hmac_matches(configured_secret, body, header_signatures) and configured_secret not in header_signatures:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")

    reference_code = _build_reference_code(payload)
    transaction_id = _build_transaction_id(payload)
    order_code = _extract_order_code(payload)
    amount = _to_decimal(
        _extract_first(
            payload,
            ["amount", "transfer_amount", "transferAmount", "creditAmount", "paid_amount", "value", "total_amount"],
        )
    )
    content = _extract_first(
        payload,
        ["content", "description", "transfer_content", "transferContent", "memo", "addInfo", "message", "note"],
    )
    bank_code = _extract_first(payload, ["bank_code", "bankCode", "bank", "bank_short_name"])
    account_number = _extract_first(payload, ["account_number", "accountNumber", "accountNo", "account"])
    account_name = _extract_first(payload, ["account_name", "accountName", "account_holder_name", "accountHolderName"])
    status_value = str(_extract_first(payload, ["status", "state", "transaction_status", "transactionStatus"]) or "SUCCESS").upper()
    transaction_time = _parse_datetime(
        _extract_first(
            payload,
            ["transaction_time", "transactionTime", "trans_time", "transTime", "created_at", "createdAt", "time"],
        )
    )

    duplicate_conditions = [PaymentWebhookEvent.reference_code == reference_code]
    if transaction_id:
        duplicate_conditions.append(PaymentWebhookEvent.transaction_id == transaction_id)
    duplicate_query = select(PaymentWebhookEvent).where(or_(*duplicate_conditions))
    duplicate_result = await db.execute(duplicate_query)
    existing_event = duplicate_result.scalar_one_or_none()
    if existing_event:
        return {"ok": True, "duplicate": True, "reference_code": existing_event.reference_code, "order_code": existing_event.order_code}

    order = await _find_order_by_code(db, order_code)
    event_status = status_value

    if not order:
        event_status = "ORDER_NOT_FOUND"
    elif amount is not None and Decimal(str(order.total_amount or 0)) != Decimal(str(amount)):
        event_status = "AMOUNT_MISMATCH"
    elif status_value not in {"SUCCESS", "PAID", "COMPLETED", "SUCCESSFUL"}:
        event_status = status_value
    else:
        if transaction_id and order.sepay_transaction_id and order.sepay_transaction_id == transaction_id:
            return {"ok": True, "duplicate": True, "reference_code": reference_code, "order_code": order.order_code}

        order.payment_status = PaymentStatus.PAID
        order.status = OrderStatus.PAID
        order.paid_at = transaction_time or datetime.now(timezone.utc)
        order.sepay_transaction_id = transaction_id
        order.sepay_reference_code = reference_code
        order.sepay_content = _normalize_text(content)
        order.sepay_raw_payload = payload

    event = PaymentWebhookEvent(
        reference_code=reference_code,
        transaction_id=transaction_id,
        order_code=order.order_code if order else order_code,
        provider="SEPAY",
        amount=amount,
        content=content,
        bank_code=bank_code,
        account_number=account_number,
        account_name=account_name,
        status=event_status,
        transaction_time=transaction_time,
        raw_payload=payload,
    )
    db.add(event)

    if order and event_status == "SUCCESS":
        await db.commit()
        await db.refresh(order)
        await db.refresh(event)
        return {
            "ok": True,
            "duplicate": False,
            "matched": True,
            "reference_code": reference_code,
            "transaction_id": transaction_id,
            "order_code": order.order_code,
            "payment_status": order.payment_status.value if hasattr(order.payment_status, "value") else str(order.payment_status),
        }

    await db.commit()
    await db.refresh(event)

    return {
        "ok": True,
        "duplicate": False,
        "matched": bool(order),
        "reference_code": reference_code,
        "transaction_id": transaction_id,
        "order_code": order.order_code if order else order_code,
        "status": event_status,
    }


@router.get("/revenue")
async def sepay_revenue_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
            func.max(Order.paid_at),
        ).where(Order.payment_status == PaymentStatus.PAID)
    )
    paid_count, total_amount, latest_paid_at = result.one()

    latest_orders_result = await db.execute(
        select(Order).where(Order.payment_status == PaymentStatus.PAID).order_by(desc(Order.paid_at), desc(Order.created_at)).limit(5)
    )
    latest_orders = latest_orders_result.scalars().all()

    return {
        "paid_count": int(paid_count or 0),
        "total_amount": str(total_amount or 0),
        "latest_paid_at": latest_paid_at,
        "latest_orders": [
            {
                "order_code": order.order_code,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "customer_email": order.customer_email,
                "total_amount": str(order.total_amount or 0),
                "payment_status": order.payment_status.value if hasattr(order.payment_status, "value") else str(order.payment_status),
                "status": order.status.value if hasattr(order.status, "value") else str(order.status),
                "paid_at": order.paid_at,
                "sepay_transaction_id": order.sepay_transaction_id,
                "sepay_reference_code": order.sepay_reference_code,
                "created_at": order.created_at,
            }
            for order in latest_orders
        ],
    }
