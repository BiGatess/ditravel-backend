from app.db import models  # noqa: F401
from app.db.database import Base, engine
from sqlalchemy import inspect, text


def _ensure_user_profile_columns(sync_conn) -> None:
    inspector = inspect(sync_conn)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "address" not in columns:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN address VARCHAR(255)"))


async def create_missing_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_user_profile_columns)
