from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.admin_bootstrap import bootstrap_admin_from_env
from app.core.db_bootstrap import create_missing_tables
from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.provinces import router as provinces_router
from app.api.places import router as places_router
from app.api.products import router as products_router
from app.api.banners import router as banners_router
from app.api.ticket_types import router as ticket_types_router
from app.api.users import router as users_router
from app.api.pricing import router as pricing_router
from app.api.reviews import router as reviews_router
from app.api.vouchers import router as vouchers_router
from app.api.blogs import router as blogs_router
from app.api.settings import router as settings_router
from app.api.sepay import router as sepay_router

fastapi_app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for DiTravel Booking System",
    version="1.0.0"
)

# Cấu hình CORS để Frontend có thể gọi API
origins = [
    settings.FRONTEND_URL,
    "https://ditravel-vietnam.vercel.app",
    "http://localhost:3000",
    "http://localhost:5173",
]

# Đăng ký các cổng API (Routers)
fastapi_app.include_router(auth_router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"])
fastapi_app.include_router(provinces_router, prefix=f"{settings.API_PREFIX}/provinces", tags=["Provinces"])
fastapi_app.include_router(places_router, prefix=f"{settings.API_PREFIX}/places", tags=["Places"])
fastapi_app.include_router(products_router, prefix=f"{settings.API_PREFIX}/products", tags=["Products (Tours)"])
fastapi_app.include_router(banners_router, prefix=f"{settings.API_PREFIX}/banners", tags=["Banners"])
fastapi_app.include_router(ticket_types_router, prefix=f"{settings.API_PREFIX}/ticket-types", tags=["Ticket Types"])
fastapi_app.include_router(users_router, prefix=f"{settings.API_PREFIX}/users", tags=["Users"])
fastapi_app.include_router(pricing_router, prefix=f"{settings.API_PREFIX}/pricing", tags=["Pricing"])
fastapi_app.include_router(reviews_router, prefix=f"{settings.API_PREFIX}/reviews", tags=["Reviews"])
fastapi_app.include_router(vouchers_router, prefix=f"{settings.API_PREFIX}/vouchers", tags=["Vouchers"])
fastapi_app.include_router(blogs_router, prefix=f"{settings.API_PREFIX}/blogs", tags=["Blogs"])
fastapi_app.include_router(settings_router, prefix=f"{settings.API_PREFIX}/settings", tags=["Settings"])
fastapi_app.include_router(sepay_router, prefix=f"{settings.API_PREFIX}/sepay", tags=["SePay"])

@fastapi_app.get("/")
def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}

@fastapi_app.on_event("startup")
async def bootstrap_admin():
    await create_missing_tables()
    await bootstrap_admin_from_env()

# Bọc CORS ngoài cùng để cả response lỗi 500 cũng có header CORS.
app = CORSMiddleware(
    fastapi_app,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
