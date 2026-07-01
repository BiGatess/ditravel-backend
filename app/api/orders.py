from decimal import Decimal
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.db.database import get_db
from app.db.models import Order, OrderStatus, PaymentStatus, User
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate

router = APIRouter()


def _enum_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip().upper() or None


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    order = Order(
        order_code=f"TEMP-{uuid.uuid4().hex}",
        payment_code=None,
        customer_name=data.customer_name.strip(),
        customer_phone=data.customer_phone.strip(),
        customer_email=data.customer_email.strip(),
        customer_address=data.customer_address.strip() if data.customer_address else None,
        items=[item.model_dump(mode="json") for item in data.items],
        total_amount=Decimal(str(data.total_amount)),
        payment_status=PaymentStatus.PENDING,
        status=OrderStatus.PENDING,
        payment_method=(data.payment_method or "SEPAY").strip().upper(),
        sepay_raw_payload=data.raw_checkout,
    )
    db.add(order)
    await db.flush()

    order.order_code = f"ORDER{order.id}"
    order.payment_code = order.order_code

    await db.commit()
    await db.refresh(order)
    return order


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    payment_status: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    stmt = select(Order).order_by(desc(Order.created_at)).limit(limit)

    normalized_status = _enum_value(status_filter)
    normalized_payment_status = _enum_value(payment_status)

    if normalized_status and normalized_status != "ALL":
        stmt = stmt.where(Order.status == normalized_status)
    if normalized_payment_status and normalized_payment_status != "ALL":
        stmt = stmt.where(Order.payment_status == normalized_payment_status)
    if q:
        query = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Order.order_code.ilike(query),
                Order.customer_name.ilike(query),
                Order.customer_phone.ilike(query),
                Order.customer_email.ilike(query),
            )
        )

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{order_code}", response_model=OrderResponse)
async def get_order(
    order_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(select(Order).where(Order.order_code == order_code))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_code}/status", response_model=OrderResponse)
async def update_order_status(
    order_code: str,
    data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(select(Order).where(Order.order_code == order_code))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = _enum_value(data.status) or order.status
    if data.payment_status:
        order.payment_status = _enum_value(data.payment_status) or order.payment_status

    await db.commit()
    await db.refresh(order)
    return order
