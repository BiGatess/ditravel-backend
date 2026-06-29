from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_admin
from app.db.database import get_db
from app.db.models import PricingRule, Product, TicketType, User
from app.schemas.pricing import PricingBulkUpsert, PricingRuleCreate, PricingRuleResponse, PricingRuleUpdate

router = APIRouter()


async def ensure_product_and_ticket(db: AsyncSession, product_id: UUID, ticket_type_id: UUID) -> None:
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=400, detail="Product does not exist")

    ticket = await db.get(TicketType, ticket_type_id)
    if not ticket or ticket.product_id != product_id:
        raise HTTPException(status_code=400, detail="Ticket type does not belong to this product")


@router.get("/", response_model=List[PricingRuleResponse])
async def list_pricing_rules(
    product_id: Optional[UUID] = None,
    ticket_type_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    query = select(PricingRule).order_by(PricingRule.date.asc())
    if product_id:
        query = query.where(PricingRule.product_id == product_id)
    if ticket_type_id:
        query = query.where(PricingRule.ticket_type_id == ticket_type_id)
    if start_date:
        query = query.where(PricingRule.date >= start_date)
    if end_date:
        query = query.where(PricingRule.date <= end_date)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=PricingRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_pricing_rule(
    data: PricingRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    await ensure_product_and_ticket(db, data.product_id, data.ticket_type_id)
    existing = await db.execute(
        select(PricingRule).where(
            PricingRule.ticket_type_id == data.ticket_type_id,
            PricingRule.date == data.date,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Pricing rule already exists for this date")

    rule = PricingRule(**data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.post("/bulk", response_model=List[PricingRuleResponse])
async def bulk_upsert_pricing_rules(
    data: PricingBulkUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    saved_rules: List[PricingRule] = []

    for record in data.records:
        await ensure_product_and_ticket(db, record.product_id, record.ticket_type_id)
        result = await db.execute(
            select(PricingRule).where(
                PricingRule.ticket_type_id == record.ticket_type_id,
                PricingRule.date == record.date,
            )
        )
        rule = result.scalar_one_or_none()
        if rule:
            for key, value in record.model_dump().items():
                setattr(rule, key, value)
        else:
            rule = PricingRule(**record.model_dump())
            db.add(rule)
        saved_rules.append(rule)

    await db.commit()
    for rule in saved_rules:
        await db.refresh(rule)
    return saved_rules


@router.put("/{rule_id}", response_model=PricingRuleResponse)
async def update_pricing_rule(
    rule_id: UUID,
    data: PricingRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    rule = await db.get(PricingRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pricing_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    rule = await db.get(PricingRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    await db.delete(rule)
    await db.commit()
    return None
