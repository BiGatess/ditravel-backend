from sqlalchemy.future import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.database import AsyncSessionLocal
from app.db.models import User, UserStatus, UserType


async def bootstrap_admin_from_env() -> None:
    if not settings.ADMIN_EMAIL:
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        user = result.scalar_one_or_none()

        if user:
            user.user_type = UserType.ADMIN
            user.status = UserStatus.ACTIVE
            await db.commit()
            print(f"Admin bootstrap: promoted {settings.ADMIN_EMAIL} to ADMIN.")
            return

        if not settings.ADMIN_PASSWORD:
            print("Admin bootstrap: ADMIN_EMAIL was set, but user does not exist and ADMIN_PASSWORD is missing.")
            return

        user = User(
            email=settings.ADMIN_EMAIL,
            full_name=settings.ADMIN_NAME,
            phone=settings.ADMIN_PHONE,
            password_hash=get_password_hash(settings.ADMIN_PASSWORD),
            user_type=UserType.ADMIN,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        await db.commit()
        print(f"Admin bootstrap: created ADMIN account for {settings.ADMIN_EMAIL}.")
