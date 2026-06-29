from app.db import models  # noqa: F401
from app.db.database import Base, engine


async def create_missing_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
