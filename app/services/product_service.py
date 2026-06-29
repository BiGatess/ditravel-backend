import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.db.models import Product, TicketType
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.province_service import generate_slug

class ProductService:
    @staticmethod
    def _min_price_from_ticket_payload(ticket_types_data) -> Decimal | None:
        active_prices = [
            tt.price if hasattr(tt, "price") else tt.get("price")
            for tt in ticket_types_data
            if (tt.is_active if hasattr(tt, "is_active") else tt.get("is_active", True))
        ]
        return min(active_prices) if active_prices else None

    @staticmethod
    async def get_min_active_ticket_price(db: AsyncSession, product_id: uuid.UUID) -> Decimal | None:
        result = await db.execute(
            select(TicketType.price)
            .where(TicketType.product_id == product_id, TicketType.is_active == True)
            .order_by(TicketType.price.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def sync_price_from_ticket_types(
        db: AsyncSession,
        product_id: uuid.UUID,
        fallback_price: Decimal | None = None,
    ) -> Decimal | None:
        product = await db.get(Product, product_id)
        if not product:
            return None

        min_price = await ProductService.get_min_active_ticket_price(db, product_id)
        product.price = min_price if min_price is not None else (fallback_price if fallback_price is not None else 0)
        return product.price

    @staticmethod
    async def get_all(db: AsyncSession):
        # Lấy Product kèm theo Place và TicketTypes
        query = select(Product).options(
            selectinload(Product.place),
            selectinload(Product.ticket_types)
        ).order_by(Product.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, product_id: uuid.UUID):
        query = select(Product).options(
            selectinload(Product.place),
            selectinload(Product.ticket_types)
        ).where(Product.id == product_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_featured(db: AsyncSession):
        """Lấy các sản phẩm nổi bật để hiển thị trang chủ"""
        query = select(Product).options(
            selectinload(Product.place),
            selectinload(Product.ticket_types)
        ).where(Product.is_featured == True).order_by(Product.created_at.desc()).limit(10)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create(db: AsyncSession, data: ProductCreate):
        slug = generate_slug(data.title)
        
        # Tách ticket_types ra khỏi product data
        ticket_types_data = data.ticket_types or []
        product_data = data.model_dump(exclude={"ticket_types"})
        min_ticket_price = ProductService._min_price_from_ticket_payload(ticket_types_data)
        if min_ticket_price is not None:
            product_data["price"] = min_ticket_price
        
        new_product = Product(
            **product_data,
            slug=slug
        )
        db.add(new_product)
        await db.flush()  # Flush để có product.id
        
        # Tạo các gói dịch vụ đi kèm
        for tt in ticket_types_data:
            ticket_type = TicketType(
                product_id=new_product.id,
                **tt.model_dump()
            )
            db.add(ticket_type)
        
        await db.commit()
        
        # Load lại đầy đủ relationships để trả về
        return await ProductService.get_by_id(db, new_product.id)

    @staticmethod
    async def update(db: AsyncSession, product_id: uuid.UUID, data: ProductUpdate):
        product = await ProductService.get_by_id(db, product_id)
        if not product:
            return None
            
        update_data = data.model_dump(exclude_unset=True)
        
        # Xử lý ticket_types nếu có trong request
        ticket_types_data = update_data.pop("ticket_types", None)
        fallback_price = update_data.get("price", product.price)
        
        if "title" in update_data:
            update_data["slug"] = generate_slug(update_data["title"])
            
        for key, value in update_data.items():
            setattr(product, key, value)
        
        # Nếu có gửi ticket_types, xóa cũ và tạo mới
        if ticket_types_data is not None:
            # Xóa tất cả ticket types cũ
            for old_tt in product.ticket_types:
                await db.delete(old_tt)
            
            # Tạo ticket types mới
            for tt_data in ticket_types_data:
                ticket_type = TicketType(
                    product_id=product_id,
                    name=tt_data["name"],
                    description=tt_data.get("description"),
                    price=tt_data["price"],
                    original_price=tt_data.get("original_price"),
                    min_quantity=tt_data.get("min_quantity", 1),
                    max_quantity=tt_data.get("max_quantity", 10),
                    is_active=tt_data.get("is_active", True)
                )
                db.add(ticket_type)

            await db.flush()
            await ProductService.sync_price_from_ticket_types(db, product_id, fallback_price=fallback_price)
            
        await db.commit()
        return await ProductService.get_by_id(db, product_id)

    @staticmethod
    async def delete(db: AsyncSession, product_id: uuid.UUID):
        product = await ProductService.get_by_id(db, product_id)
        if not product:
            return False
            
        await db.delete(product)
        await db.commit()
        return True
