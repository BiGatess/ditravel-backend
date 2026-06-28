from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import User
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.services.product_service import ProductService
from app.services.place_service import PlaceService
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=List[ProductResponse])
async def read_products(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách tất cả Sản phẩm/Tour (Công khai)"""
    return await ProductService.get_all(db)

@router.get("/featured", response_model=List[ProductResponse])
async def read_featured_products(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách Tour nổi bật cho Trang chủ (Công khai)"""
    return await ProductService.get_featured(db)

@router.get("/{product_id}", response_model=ProductResponse)
async def read_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    """Lấy chi tiết một Tour (Công khai)"""
    product = await ProductService.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm này")
    return product

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Thêm Tour mới (Yêu cầu đăng nhập Admin)"""
    if current_user.user_type.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện")
        
    # Ràng buộc: Kiểm tra place_id có tồn tại không
    place = await PlaceService.get_by_id(db, data.place_id)
    if not place:
        raise HTTPException(status_code=400, detail="Địa điểm (Place) không tồn tại")
        
    return await ProductService.create(db, data)

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cập nhật thông tin Tour (Yêu cầu đăng nhập Admin)"""
    if current_user.user_type.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện")
        
    if data.place_id:
        place = await PlaceService.get_by_id(db, data.place_id)
        if not place:
            raise HTTPException(status_code=400, detail="Địa điểm mới không tồn tại")
            
    product = await ProductService.update(db, product_id, data)
    if not product:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm này")
    return product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Xóa Tour (Yêu cầu đăng nhập Admin)"""
    if current_user.user_type.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện")
        
    success = await ProductService.delete(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm này")
    return None
