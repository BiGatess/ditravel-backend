from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.database import get_db
from app.db.models import User, UserType, UserStatus
from app.schemas.user import UserResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[UserResponse])
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()

@router.patch("/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    if str(current_user.id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.status = UserStatus.BLOCKED if user.status == UserStatus.ACTIVE else UserStatus.ACTIVE
    await db.commit()
    
    return {"message": "Success", "status": user.status}
