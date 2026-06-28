import asyncio
from app.db.database import engine
from sqlalchemy import text

async def alter_tables():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE products ADD COLUMN category VARCHAR(50) DEFAULT 'TOUR';"))

if __name__ == "__main__":
    asyncio.run(alter_tables())
