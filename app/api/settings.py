from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_admin
from app.db.database import get_db
from app.db.models import SystemSetting, User
from app.schemas.setting import SystemSettingCreate, SystemSettingResponse, SystemSettingUpdate

router = APIRouter()


@router.get("/public")
async def get_public_settings(
    keys: str = Query(..., description="Comma-separated setting keys"),
    db: AsyncSession = Depends(get_db),
):
    key_list = [key.strip() for key in keys.split(",") if key.strip()]
    if not key_list:
        return {}

    result = await db.execute(select(SystemSetting).where(SystemSetting.key.in_(key_list)))
    settings = result.scalars().all()
    return {setting.key: setting.value for setting in settings}


@router.get("/", response_model=List[SystemSettingResponse])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.key.asc()))
    return result.scalars().all()


@router.get("/{key}", response_model=SystemSettingResponse)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting


@router.put("/{key}", response_model=SystemSettingResponse)
async def upsert_setting(
    key: str,
    data: SystemSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = SystemSetting(key=key, value=data.value, description=data.description)
        db.add(setting)
    else:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(setting, field, value)

    await db.commit()
    await db.refresh(setting)
    return setting


@router.post("/", response_model=SystemSettingResponse, status_code=status.HTTP_201_CREATED)
async def create_setting(
    data: SystemSettingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    existing = await db.execute(select(SystemSetting).where(SystemSetting.key == data.key))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Setting key already exists")

    setting = SystemSetting(**data.model_dump())
    db.add(setting)
    await db.commit()
    await db.refresh(setting)
    return setting


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    await db.delete(setting)
    await db.commit()
    return None
