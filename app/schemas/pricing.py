from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.db.models import PricingStatus


class PricingRuleBase(BaseModel):
    product_id: UUID
    ticket_type_id: UUID
    date: date
    price: Decimal
    original_price: Optional[Decimal] = None
    stock: int = 0
    status: PricingStatus = PricingStatus.OPEN
    note: Optional[str] = None


class PricingRuleCreate(PricingRuleBase):
    pass


class PricingRuleUpdate(BaseModel):
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    stock: Optional[int] = None
    status: Optional[PricingStatus] = None
    note: Optional[str] = None


class PricingBulkUpsert(BaseModel):
    records: List[PricingRuleCreate]


class PricingRuleResponse(PricingRuleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
