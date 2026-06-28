import asyncio
from app.db.database import engine, Base
import app.db.models  # Import models để SQLAlchemy biết các bảng cần tạo

async def init_db():
    async with engine.begin() as conn:
        print("Tạo các bảng...")
        # Tạo tất cả các bảng nếu chưa có
        await conn.run_sync(Base.metadata.create_all)
        print("Hoàn tất!")

if __name__ == "__main__":
    asyncio.run(init_db())
