import re
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import Province
from app.schemas.province import ProvinceCreate, ProvinceUpdate

def generate_slug(text: str) -> str:
    """Hàm tự động tạo đường dẫn thân thiện (VD: Đà Nẵng -> da-nang)"""
    # Xoá dấu tiếng Việt
    text = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', text)
    text = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', text)
    text = re.sub(r'[ìíịỉĩ]', 'i', text)
    text = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', text)
    text = re.sub(r'[ùúụủũưừứựửữ]', 'u', text)
    text = re.sub(r'[ỳýỵỷỹ]', 'y', text)
    text = re.sub(r'[đ]', 'd', text)
    text = re.sub(r'[ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴ]', 'A', text)
    text = re.sub(r'[ÈÉẸẺẼÊỀẾỆỂỄ]', 'E', text)
    text = re.sub(r'[ÌÍỊỈĨ]', 'I', text)
    text = re.sub(r'[ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ]', 'O', text)
    text = re.sub(r'[ÙÚỤỦŨƯỪỨỰỬỮ]', 'U', text)
    text = re.sub(r'[ỲÝỴỶỸ]', 'Y', text)
    text = re.sub(r'[Đ]', 'D', text)
    
    # Chuyển thành chữ thường và thay khoảng trắng bằng dấu gạch ngang
    text = text.lower()
    text = re.sub(r'[^a-z0-9\-]', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text

class ProvinceService:
    @staticmethod
    async def get_all(db: AsyncSession):
        query = select(Province).order_by(Province.name)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, province_id: UUID):
        query = select(Province).where(Province.id == province_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: ProvinceCreate):
        slug = generate_slug(data.name)
        new_province = Province(
            **data.model_dump(),
            slug=slug
        )
        db.add(new_province)
        await db.commit()
        await db.refresh(new_province)
        return new_province

    @staticmethod
    async def update(db: AsyncSession, province_id: UUID, data: ProvinceUpdate):
        province = await ProvinceService.get_by_id(db, province_id)
        if not province:
            return None
            
        update_data = data.model_dump(exclude_unset=True)
        
        # Nếu đổi tên thì tự động đổi lại slug
        if "name" in update_data:
            update_data["slug"] = generate_slug(update_data["name"])
            
        for key, value in update_data.items():
            setattr(province, key, value)
            
        await db.commit()
        await db.refresh(province)
        return province

    @staticmethod
    async def delete(db: AsyncSession, province_id: UUID):
        province = await ProvinceService.get_by_id(db, province_id)
        if not province:
            return False
            
        await db.delete(province)
        await db.commit()
        return True
