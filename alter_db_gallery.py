import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def alter_db():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE products ADD COLUMN gallery JSON"))
            print("Successfully added gallery column")
        except Exception as e:
            print("Error altering table:", e)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(alter_db())
