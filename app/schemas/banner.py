from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.db.models import BannerPosition

class BannerBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: str
    link: Optional[str] = None
    position: BannerPosition = BannerPosition.HOME_MAIN
    order: int = 0
    is_active: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class BannerCreate(BannerBase):
    pass

class BannerUpdate(BannerBase):
    title: Optional[str] = None
    image_url: Optional[str] = None

class BannerResponse(BannerBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BannerOrderUpdate(BaseModel):
    id: UUID
    order: int
