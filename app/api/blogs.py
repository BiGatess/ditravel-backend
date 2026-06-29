from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_admin
from app.db.database import get_db
from app.db.models import BlogPost, BlogStatus, User
from app.schemas.blog import BlogPostCreate, BlogPostResponse, BlogPostUpdate
from app.services.province_service import generate_slug

router = APIRouter()


async def make_unique_slug(db: AsyncSession, base_slug: str, current_id: Optional[UUID] = None) -> str:
    slug = base_slug or "blog-post"
    candidate = slug
    suffix = 2
    while True:
        query = select(BlogPost).where(BlogPost.slug == candidate)
        if current_id:
            query = query.where(BlogPost.id != current_id)
        result = await db.execute(query)
        if not result.scalar_one_or_none():
            return candidate
        candidate = f"{slug}-{suffix}"
        suffix += 1


@router.get("/", response_model=List[BlogPostResponse])
async def list_blog_posts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(select(BlogPost).order_by(BlogPost.created_at.desc()))
    return result.scalars().all()


@router.get("/public", response_model=List[BlogPostResponse])
async def list_public_blog_posts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.status == BlogStatus.PUBLISHED)
        .order_by(BlogPost.published_at.desc().nullslast(), BlogPost.created_at.desc())
    )
    return result.scalars().all()


@router.get("/slug/{slug}", response_model=BlogPostResponse)
async def get_public_blog_post_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BlogPost).where(BlogPost.slug == slug, BlogPost.status == BlogStatus.PUBLISHED)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    return post


@router.get("/{post_id}", response_model=BlogPostResponse)
async def get_blog_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    post = await db.get(BlogPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    return post


@router.post("/", response_model=BlogPostResponse, status_code=status.HTTP_201_CREATED)
async def create_blog_post(
    data: BlogPostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    payload = data.model_dump()
    requested_slug = payload.pop("slug", None)
    payload["slug"] = await make_unique_slug(db, generate_slug(requested_slug or data.title))
    if payload.get("status") == BlogStatus.PUBLISHED and not payload.get("published_at"):
        payload["published_at"] = datetime.utcnow()

    post = BlogPost(**payload)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@router.put("/{post_id}", response_model=BlogPostResponse)
async def update_blog_post(
    post_id: UUID,
    data: BlogPostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    post = await db.get(BlogPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")

    update_data = data.model_dump(exclude_unset=True)
    if "slug" in update_data and update_data["slug"]:
        update_data["slug"] = await make_unique_slug(db, generate_slug(update_data["slug"]), post_id)
    elif "title" in update_data:
        update_data["slug"] = await make_unique_slug(db, generate_slug(update_data["title"]), post_id)

    if update_data.get("status") == BlogStatus.PUBLISHED and not post.published_at and not update_data.get("published_at"):
        update_data["published_at"] = datetime.utcnow()

    for key, value in update_data.items():
        setattr(post, key, value)

    await db.commit()
    await db.refresh(post)
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blog_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    post = await db.get(BlogPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    await db.delete(post)
    await db.commit()
    return None
