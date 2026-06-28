import asyncio
from app.db.database import engine
from sqlalchemy import text

async def alter_tables():
    async with engine.begin() as conn:
        print("Đang thay đổi kiểu dữ liệu cột hình ảnh sang TEXT...")
        await conn.execute(text("ALTER TABLE provinces ALTER COLUMN image TYPE TEXT;"))
        await conn.execute(text("ALTER TABLE places ALTER COLUMN image TYPE TEXT;"))
        await conn.execute(text("ALTER TABLE products ALTER COLUMN image TYPE TEXT;"))
        await conn.execute(text("ALTER TABLE banners ALTER COLUMN image_url TYPE TEXT;"))
        print("Hoàn tất!")

if __name__ == "__main__":
    asyncio.run(alter_tables())
