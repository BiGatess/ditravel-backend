from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import ReviewStatus


class ReviewBase(BaseModel):
    product_id: Optional[UUID] = None
    product_name: str
    user_name: str
    user_avatar: Optional[str] = None
    rating: int = Field(ge=1, le=5)
    content: str
    status: ReviewStatus = ReviewStatus.PENDING
    admin_reply: Optional[str] = None


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    product_id: Optional[UUID] = None
    product_name: Optional[str] = None
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    content: Optional[str] = None
    status: Optional[ReviewStatus] = None
    admin_reply: Optional[str] = None


class ReviewStatusUpdate(BaseModel):
    status: ReviewStatus
    admin_reply: Optional[str] = None


class ReviewResponse(ReviewBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
