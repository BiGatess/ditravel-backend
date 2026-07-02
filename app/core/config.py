from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "DI_TRAVEL_API"
    APP_ENV: str = "development"
    API_PREFIX: str = "/api"
    FRONTEND_URL: str = "http://localhost:5173"

    # Database Settings
    DATABASE_URL: str
    
    # Email delivery via Resend
    RESEND_API_KEY: Optional[str] = None
    EMAIL_FROM: Optional[str] = None

    # SePay Settings
    SEPAY_WEBHOOK_SECRET: Optional[str] = None
    SEPAY_API_TOKEN: Optional[str] = None

    # Optional admin bootstrap for hosts without shell access
    ADMIN_EMAIL: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None
    ADMIN_NAME: str = "DiTravel Admin"
    ADMIN_PHONE: Optional[str] = None
    
    # JWT & Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        # Chuyển đổi URL postgresql:// thành postgresql+asyncpg:// để dùng Async
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.DATABASE_URL

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache()
def get_settings() -> Settings:
    """
    Sử dụng lru_cache để chỉ đọc file .env một lần duy nhất lúc khởi động,
    giúp tăng tốc độ xử lý của API.
    """
    return Settings()

settings = get_settings()
