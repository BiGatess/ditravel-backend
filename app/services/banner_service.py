from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, update
from fastapi import HTTPException
from uuid import UUID
from typing import List

from app.db.models import Banner
from app.schemas.banner import BannerCreate, BannerUpdate, BannerOrderUpdate

class BannerService:

    @staticmethod
    async def get_all_banners(db: AsyncSession) -> List[Banner]:
        result = await db.execute(
            select(Banner).order_by(Banner.order.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_active_banners(db: AsyncSession) -> List[Banner]:
        result = await db.execute(
            select(Banner).filter(Banner.is_active == True).order_by(Banner.order.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def create_banner(db: AsyncSession, banner_data: BannerCreate) -> Banner:
        # Lấy order lớn nhất hiện tại
        result = await db.execute(select(Banner).order_by(desc(Banner.order)).limit(1))
        last_banner = result.scalar_one_or_none()
        next_order = (last_banner.order + 1) if last_banner else 0

        db_banner = Banner(**banner_data.model_dump())
        db_banner.order = next_order
        db.add(db_banner)
        await db.commit()
        await db.refresh(db_banner)
        return db_banner

    @staticmethod
    async def update_banner(db: AsyncSession, banner_id: UUID, banner_data: BannerUpdate) -> Banner:
        result = await db.execute(select(Banner).filter(Banner.id == banner_id))
        db_banner = result.scalar_one_or_none()
        
        if not db_banner:
            raise HTTPException(status_code=404, detail="Banner not found")
            
        update_data = banner_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_banner, key, value)
            
        await db.commit()
        await db.refresh(db_banner)
        return db_banner

    @staticmethod
    async def delete_banner(db: AsyncSession, banner_id: UUID) -> dict:
        result = await db.execute(select(Banner).filter(Banner.id == banner_id))
        db_banner = result.scalar_one_or_none()
        
        if not db_banner:
            raise HTTPException(status_code=404, detail="Banner not found")
            
        await db.delete(db_banner)
        await db.commit()
        return {"message": "Xóa banner thành công"}

    @staticmethod
    async def update_banner_order(db: AsyncSession, order_updates: List[BannerOrderUpdate]) -> dict:
        for item in order_updates:
            await db.execute(
                update(Banner).where(Banner.id == item.id).values(order=item.order)
            )
        await db.commit()
        return {"message": "Cập nhật thứ tự thành công"}
