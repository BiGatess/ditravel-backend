import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import AsyncSessionLocal
from app.db.models import User, UserType

async def make_admin():
    async with AsyncSessionLocal() as db:
        query = select(User).where(User.email == 'thachhbaoloc@gmail.com')
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if user:
            user.user_type = UserType.ADMIN
            await db.commit()
            print('Đã cấp quyền ADMIN thành công!')
        else:
            print('Không tìm thấy User')

asyncio.run(make_admin())
