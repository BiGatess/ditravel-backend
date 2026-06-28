from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Khởi tạo Async Engine
# pool_size=20, max_overflow=10 giúp chống nghẽn khi có quá nhiều người dùng truy cập cùng lúc
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False, # Đặt thành True nếu muốn log ra câu lệnh SQL để debug
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True # Tự động kiểm tra kết nối xem có bị rớt không trước khi query
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class cho tất cả các Models
Base = declarative_base()

# Dependency để sử dụng trong API
async def get_db():
    """
    Hàm này cung cấp database session cho mỗi request (API).
    Tự động đóng kết nối (yield) sau khi request hoàn thành, chống rò rỉ bộ nhớ.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
