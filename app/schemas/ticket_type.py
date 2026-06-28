from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from decimal import Decimal

class TicketTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    original_price: Optional[Decimal] = None
    min_quantity: int = 1
    max_quantity: int = 10
    is_active: bool = True

class TicketTypeCreate(TicketTypeBase):
    product_id: UUID

class TicketTypeInline(BaseModel):
    """Schema for creating ticket types inline with product creation"""
    name: str
    description: Optional[str] = None
    price: Decimal
    original_price: Optional[Decimal] = None
    min_quantity: int = 1
    max_quantity: int = 10
    is_active: bool = True

class TicketTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    is_active: Optional[bool] = None

class TicketTypeResponse(TicketTypeBase):
    id: UUID
    product_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
