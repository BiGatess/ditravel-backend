from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.db.models import DiscountType, VoucherStatus


class VoucherBase(BaseModel):
    code: str
    title: str
    description: Optional[str] = None
    discount_type: DiscountType = DiscountType.PERCENT
    discount_value: Decimal
    min_order_value: Optional[Decimal] = None
    max_discount_value: Optional[Decimal] = None
    usage_limit: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: VoucherStatus = VoucherStatus.ACTIVE
    is_active: bool = True


class VoucherCreate(VoucherBase):
    pass


class VoucherUpdate(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[Decimal] = None
    min_order_value: Optional[Decimal] = None
    max_discount_value: Optional[Decimal] = None
    usage_limit: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[VoucherStatus] = None
    is_active: Optional[bool] = None


class VoucherResponse(VoucherBase):
    id: UUID
    used_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
