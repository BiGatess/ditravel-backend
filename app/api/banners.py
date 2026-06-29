from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.database import get_db
from app.db.models import User
from app.schemas.banner import BannerCreate, BannerUpdate, BannerResponse, BannerOrderUpdate
from app.services.banner_service import BannerService
from app.api.deps import get_current_user

router = APIRouter()

def require_admin(current_user: User) -> None:
    if current_user.user_type.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện")

@router.get("/", response_model=List[BannerResponse])
async def get_banners(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách tất cả banners (cho Admin)"""
    return await BannerService.get_all_banners(db)

@router.get("/active", response_model=List[BannerResponse])
async def get_active_banners(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách banners đang hiển thị (cho Frontend User)"""
    return await BannerService.get_active_banners(db)

@router.post("/", response_model=BannerResponse, status_code=status.HTTP_201_CREATED)
async def create_banner(
    banner_in: BannerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Tạo mới một banner"""
    require_admin(current_user)
    return await BannerService.create_banner(db, banner_in)

@router.put("/{banner_id}", response_model=BannerResponse)
async def update_banner(
    banner_id: UUID,
    banner_in: BannerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cập nhật thông tin banner"""
    require_admin(current_user)
    return await BannerService.update_banner(db, banner_id, banner_in)

@router.delete("/{banner_id}", status_code=status.HTTP_200_OK)
async def delete_banner(
    banner_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Xóa một banner"""
    require_admin(current_user)
    return await BannerService.delete_banner(db, banner_id)

@router.patch("/order", status_code=status.HTTP_200_OK)
async def update_banner_order(
    orders: List[BannerOrderUpdate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cập nhật thứ tự hiển thị của các banner"""
    require_admin(current_user)
    return await BannerService.update_banner_order(db, orders)
