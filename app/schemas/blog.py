from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.db.models import BlogStatus


class BlogPostBase(BaseModel):
    title: str
    excerpt: Optional[str] = None
    content: Optional[str] = None
    cover_image: Optional[str] = None
    author_name: Optional[str] = None
    status: BlogStatus = BlogStatus.DRAFT
    is_featured: bool = False
    published_at: Optional[datetime] = None


class BlogPostCreate(BlogPostBase):
    slug: Optional[str] = None


class BlogPostUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    cover_image: Optional[str] = None
    author_name: Optional[str] = None
    status: Optional[BlogStatus] = None
    is_featured: Optional[bool] = None
    published_at: Optional[datetime] = None


class BlogPostResponse(BlogPostBase):
    id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
