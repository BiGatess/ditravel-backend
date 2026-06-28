from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import User
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeUpdate, TicketTypeResponse
from app.services.ticket_type_service import TicketTypeService
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/product/{product_id}", response_model=List[TicketTypeResponse])
async def read_ticket_types_by_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    """Lấy danh sách Gói dịch vụ của một Tour (Công khai)"""
    return await TicketTypeService.get_by_product_id(db, product_id)

@router.post("/", response_model=TicketTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket_type(
    data: TicketTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Thêm Gói dịch vụ mới (Yêu cầu đăng nhập Admin)"""
    if current_user.user_type.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện")
        
    return await TicketTypeService.create(db, data)

@router.put("/{ticket_id}", response_model=TicketTypeResponse)
async def update_ticket_type(
    ticket_id: UUID,
    data: TicketTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cập nhật thông tin Gói dịch vụ (Yêu cầu đăng nhập Admin)"""
    if current_user.user_type.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện")
            
    ticket = await TicketTypeService.update(db, ticket_id, data)
    if not ticket:
        raise HTTPException(status_code=404, detail="Không tìm thấy gói dịch vụ này")
    return ticket

@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket_type(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Xóa Gói dịch vụ (Yêu cầu đăng nhập Admin)"""
    if current_user.user_type.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện")
        
    success = await TicketTypeService.delete(db, ticket_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy gói dịch vụ này")
    return None
