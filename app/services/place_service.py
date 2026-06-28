from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.db.models import Place
from app.schemas.place import PlaceCreate, PlaceUpdate
from app.services.province_service import generate_slug

class PlaceService:
    @staticmethod
    async def get_all(db: AsyncSession):
        # selectinload giúp lấy luôn cả thông tin bảng Province dính kèm
        query = select(Place).options(selectinload(Place.province)).order_by(Place.name)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, place_id: UUID):
        query = select(Place).options(selectinload(Place.province)).where(Place.id == place_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: PlaceCreate):
        slug = generate_slug(data.name)
        new_place = Place(
            **data.model_dump(),
            slug=slug
        )
        db.add(new_place)
        await db.commit()
        
        # Load lại với đầy đủ relationship để trả về
        query = select(Place).options(selectinload(Place.province)).where(Place.id == new_place.id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def update(db: AsyncSession, place_id: UUID, data: PlaceUpdate):
        place = await PlaceService.get_by_id(db, place_id)
        if not place:
            return None
            
        update_data = data.model_dump(exclude_unset=True)
        
        if "name" in update_data:
            update_data["slug"] = generate_slug(update_data["name"])
            
        for key, value in update_data.items():
            setattr(place, key, value)
            
        await db.commit()
        
        # Load lại với đầy đủ relationship để trả về
        query = select(Place).options(selectinload(Place.province)).where(Place.id == place.id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def delete(db: AsyncSession, place_id: UUID):
        place = await PlaceService.get_by_id(db, place_id)
        if not place:
            return False
            
        await db.delete(place)
        await db.commit()
        return True
