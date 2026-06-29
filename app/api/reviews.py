from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_admin
from app.db.database import get_db
from app.db.models import Product, Review, ReviewStatus, User
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewStatusUpdate, ReviewUpdate

router = APIRouter()


@router.get("/", response_model=List[ReviewResponse])
async def list_reviews(
    status_filter: Optional[ReviewStatus] = None,
    rating: Optional[int] = None,
    product_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    query = select(Review).order_by(Review.created_at.desc())
    if status_filter:
        query = query.where(Review.status == status_filter)
    if rating:
        query = query.where(Review.rating == rating)
    if product_id:
        query = query.where(Review.product_id == product_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/product/{product_id}", response_model=List[ReviewResponse])
async def list_public_product_reviews(product_id: UUID, db: AsyncSession = Depends(get_db)):
    query = (
        select(Review)
        .where(Review.product_id == product_id, Review.status == ReviewStatus.APPROVED)
        .order_by(Review.created_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    data: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if data.product_id:
        product = await db.get(Product, data.product_id)
        if not product:
            raise HTTPException(status_code=400, detail="Product does not exist")

    review = Review(**data.model_dump())
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: UUID,
    data: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("product_id"):
        product = await db.get(Product, update_data["product_id"])
        if not product:
            raise HTTPException(status_code=400, detail="Product does not exist")

    for key, value in update_data.items():
        setattr(review, key, value)

    await db.commit()
    await db.refresh(review)
    return review


@router.patch("/{review_id}/status", response_model=ReviewResponse)
async def update_review_status(
    review_id: UUID,
    data: ReviewStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.status = data.status
    if data.admin_reply is not None:
        review.admin_reply = data.admin_reply

    await db.commit()
    await db.refresh(review)
    return review


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    await db.delete(review)
    await db.commit()
    return None
