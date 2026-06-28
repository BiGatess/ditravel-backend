from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import User
from app.schemas.province import ProvinceCreate, ProvinceUpdate, ProvinceResponse
from app.services.province_service import ProvinceService
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=List[ProvinceResponse])
async def read_provinces(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách tất cả Tỉnh thành (Công khai)"""
    return await ProvinceService.get_all(db)


@router.get("/{province_id}", response_model=ProvinceResponse)
async def read_province(province_id: UUID, db: AsyncSession = Depends(get_db)):
    """Lấy chi tiết một Tỉnh thành (Công khai)"""
    province = await ProvinceService.get_by_id(db, province_id)
    if not province:
        raise HTTPException(status_code=404, detail="Không tìm thấy tỉnh thành này")
    return province


@router.post("/", response_model=ProvinceResponse, status_code=status.HTTP_201_CREATED)
async def create_province(
    data: ProvinceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Thêm Tỉnh thành mới (Yêu cầu đăng nhập)"""
    if current_user.user_type.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện")
        
    return await ProvinceService.create(db, data)


@router.put("/{province_id}", response_model=ProvinceResponse)
async def update_province(
    province_id: UUID,
    data: ProvinceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cập nhật thông tin Tỉnh thành (Yêu cầu đăng nhập)"""
    if current_user.user_type.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện")
        
    province = await ProvinceService.update(db, province_id, data)
    if not province:
        raise HTTPException(status_code=404, detail="Không tìm thấy tỉnh thành này")
    return province


@router.delete("/{province_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_province(
    province_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Xóa Tỉnh thành (Yêu cầu đăng nhập)"""
    if current_user.user_type.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện")
        
    success = await ProvinceService.delete(db, province_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy tỉnh thành này")
    return None
