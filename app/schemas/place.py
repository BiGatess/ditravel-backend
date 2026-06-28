from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.schemas.province import ProvinceResponse

class PlaceBase(BaseModel):
    name: str
    province_id: UUID
    category: Optional[str] = None
    address: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
    is_featured: bool = False
    is_active: bool = True

class PlaceCreate(PlaceBase):
    pass

class PlaceUpdate(PlaceBase):
    name: Optional[str] = None
    province_id: Optional[UUID] = None

class PlaceResponse(PlaceBase):
    id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime
    
    # Cho phép lồng thông tin Tỉnh thành vào Địa điểm khi trả về
    province: Optional[ProvinceResponse] = None

    class Config:
        from_attributes = True
