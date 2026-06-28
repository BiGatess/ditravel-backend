from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class ProvinceBase(BaseModel):
    name: str
    region: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True

class ProvinceCreate(ProvinceBase):
    pass

class ProvinceUpdate(ProvinceBase):
    name: Optional[str] = None

class ProvinceResponse(ProvinceBase):
    id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
