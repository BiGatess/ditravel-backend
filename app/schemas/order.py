from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, field_validator

from app.core.currency import normalize_vnd_price


class OrderItemSnapshot(BaseModel):
    cart_item_id: Optional[str] = None
    product_name: str
    ticket_name: Optional[str] = None
    use_date: Optional[str] = None
    quantity: int = 1
    unit_price: Decimal
    line_total: Decimal
    image: Optional[str] = None

    @field_validator("unit_price", "line_total", mode="before")
    @classmethod
    def normalize_prices(cls, value):
        return normalize_vnd_price(value)


class OrderCreate(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: str
    customer_address: Optional[str] = None
    items: list[OrderItemSnapshot]
    total_amount: Decimal
    payment_method: Optional[str] = "SEPAY"
    payment_status: Optional[str] = "PENDING"
    status: Optional[str] = "PENDING"
    raw_checkout: Optional[dict[str, Any]] = None

    @field_validator("total_amount", mode="before")
    @classmethod
    def normalize_total(cls, value):
        return normalize_vnd_price(value)


class OrderStatusUpdate(BaseModel):
    status: str
    payment_status: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    order_code: str
    payment_code: Optional[str] = None
    customer_name: str
    customer_phone: str
    customer_email: str
    customer_address: Optional[str] = None
    items: list[OrderItemSnapshot]
    total_amount: Decimal
    payment_status: str
    status: str
    payment_method: str
    paid_at: Optional[datetime] = None
    sepay_transaction_id: Optional[str] = None
    sepay_reference_code: Optional[str] = None
    sepay_content: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
