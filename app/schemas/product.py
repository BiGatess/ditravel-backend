from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from app.core.currency import normalize_vnd_price
from .ticket_type import TicketTypeResponse, TicketTypeInline

# Giả sử chúng ta muốn trả về tên Place cùng với Product
class PlaceSimpleResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    image: Optional[str] = None
    gallery: Optional[List[str]] = []
    
    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    title: str
    place_id: UUID
    price: Decimal
    duration: Optional[str] = None
    image: Optional[str] = None
    gallery: Optional[List[str]] = []
    description: Optional[str] = None
    
    highlights: Optional[str] = None
    terms: Optional[str] = None
    cancellation_policy: Optional[str] = None
    usage_guide: Optional[str] = None
    
    category: Optional[str] = "TOUR"
    is_featured: bool = False
    is_active: bool = True

    @field_validator("price", mode="before")
    @classmethod
    def normalize_price(cls, value):
        return normalize_vnd_price(value)

class ProductCreate(ProductBase):
    ticket_types: Optional[List[TicketTypeInline]] = []

class ProductUpdate(ProductBase):
    title: Optional[str] = None
    place_id: Optional[UUID] = None
    price: Optional[Decimal] = None
    highlights: Optional[str] = None
    terms: Optional[str] = None
    cancellation_policy: Optional[str] = None
    usage_guide: Optional[str] = None
    category: Optional[str] = None
    is_featured: Optional[bool] = None
    ticket_types: Optional[List[TicketTypeInline]] = None

class ProductResponse(ProductBase):
    id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime
    
    # Kèm thông tin Place rút gọn (bao gồm gallery ảnh)
    place: Optional[PlaceSimpleResponse] = None
    
    # Danh sách gói dịch vụ
    ticket_types: Optional[list['TicketTypeResponse']] = []

    class Config:
        from_attributes = True
