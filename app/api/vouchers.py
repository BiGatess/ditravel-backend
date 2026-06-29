from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_admin
from app.db.database import get_db
from app.db.models import User, Voucher
from app.schemas.voucher import VoucherCreate, VoucherResponse, VoucherUpdate

router = APIRouter()


@router.get("/", response_model=List[VoucherResponse])
async def list_vouchers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(select(Voucher).order_by(Voucher.created_at.desc()))
    return result.scalars().all()


@router.get("/{voucher_id}", response_model=VoucherResponse)
async def get_voucher(
    voucher_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    voucher = await db.get(Voucher, voucher_id)
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    return voucher


@router.post("/", response_model=VoucherResponse, status_code=status.HTTP_201_CREATED)
async def create_voucher(
    data: VoucherCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    payload = data.model_dump()
    payload["code"] = payload["code"].strip().upper()
    existing = await db.execute(select(Voucher).where(Voucher.code == payload["code"]))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Voucher code already exists")

    voucher = Voucher(**payload)
    db.add(voucher)
    await db.commit()
    await db.refresh(voucher)
    return voucher


@router.put("/{voucher_id}", response_model=VoucherResponse)
async def update_voucher(
    voucher_id: UUID,
    data: VoucherUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    voucher = await db.get(Voucher, voucher_id)
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")

    update_data = data.model_dump(exclude_unset=True)
    if "code" in update_data and update_data["code"]:
        update_data["code"] = update_data["code"].strip().upper()
        existing = await db.execute(
            select(Voucher).where(Voucher.code == update_data["code"], Voucher.id != voucher_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Voucher code already exists")

    for key, value in update_data.items():
        setattr(voucher, key, value)

    await db.commit()
    await db.refresh(voucher)
    return voucher


@router.delete("/{voucher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voucher(
    voucher_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    voucher = await db.get(Voucher, voucher_id)
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    await db.delete(voucher)
    await db.commit()
    return None
