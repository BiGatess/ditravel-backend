import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import TicketType
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeUpdate

class TicketTypeService:
    @staticmethod
    async def get_by_product_id(db: AsyncSession, product_id: uuid.UUID):
        query = select(TicketType).where(TicketType.product_id == product_id).order_by(TicketType.created_at.asc())
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, ticket_id: uuid.UUID):
        query = select(TicketType).where(TicketType.id == ticket_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: TicketTypeCreate):
        new_ticket = TicketType(**data.model_dump())
        db.add(new_ticket)
        await db.commit()
        await db.refresh(new_ticket)
        return new_ticket

    @staticmethod
    async def update(db: AsyncSession, ticket_id: uuid.UUID, data: TicketTypeUpdate):
        ticket = await TicketTypeService.get_by_id(db, ticket_id)
        if not ticket:
            return None
            
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(ticket, key, value)
            
        await db.commit()
        await db.refresh(ticket)
        return ticket

    @staticmethod
    async def delete(db: AsyncSession, ticket_id: uuid.UUID):
        ticket = await TicketTypeService.get_by_id(db, ticket_id)
        if not ticket:
            return False
            
        await db.delete(ticket)
        await db.commit()
        return True
