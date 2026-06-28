from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import User
from app.schemas.place import PlaceCreate, PlaceUpdate, PlaceResponse
from app.services.place_service import PlaceService
from app.services.province_service import ProvinceService
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=List[PlaceResponse])
async def read_places(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách tất cả Địa điểm (Công khai)"""
    return await PlaceService.get_all(db)


@router.get("/{place_id}", response_model=PlaceResponse)
async def read_place(place_id: UUID, db: AsyncSession = Depends(get_db)):
    """Lấy chi tiết một Địa điểm (Công khai)"""
    place = await PlaceService.get_by_id(db, place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm này")
    return place


@router.post("/", response_model=PlaceResponse, status_code=status.HTTP_201_CREATED)
async def create_place(
    data: PlaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Thêm Địa điểm mới (Yêu cầu đăng nhập)"""
    if current_user.user_type.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện")
        
    # Ràng buộc: Kiểm tra province_id có tồn tại không
    province = await ProvinceService.get_by_id(db, data.province_id)
    if not province:
        raise HTTPException(status_code=400, detail="Tỉnh/Thành phố không tồn tại")
        
    return await PlaceService.create(db, data)


@router.put("/{place_id}", response_model=PlaceResponse)
async def update_place(
    place_id: UUID,
    data: PlaceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cập nhật thông tin Địa điểm (Yêu cầu đăng nhập)"""
    if current_user.user_type.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện")
        
    # Ràng buộc: Nếu có đổi province_id thì phải kiểm tra xem có tồn tại không
    if data.province_id:
        province = await ProvinceService.get_by_id(db, data.province_id)
        if not province:
            raise HTTPException(status_code=400, detail="Tỉnh/Thành phố mới không tồn tại")
            
    place = await PlaceService.update(db, place_id, data)
    if not place:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm này")
    return place


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_place(
    place_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Xóa Địa điểm (Yêu cầu đăng nhập)"""
    if current_user.user_type.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện")
        
    success = await PlaceService.delete(db, place_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm này")
    return None
