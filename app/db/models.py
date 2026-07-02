import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Date, ForeignKey, Integer, Text, Enum, Numeric, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.db.database import Base

# === Định nghĩa Enums (Giới hạn giá trị của cột) ===
class UserType(str, enum.Enum):
    ADMIN = "ADMIN"
    USER = "USER"

class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"

class BannerPosition(str, enum.Enum):
    HOME_MAIN = "HOME_MAIN"
    HOME_SUB = "HOME_SUB"
    POPUP = "POPUP"

class PricingStatus(str, enum.Enum):
    OPEN = "OPEN"
    FULL = "FULL"
    CLOSED = "CLOSED"

class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    HIDDEN = "hidden"

class DiscountType(str, enum.Enum):
    PERCENT = "PERCENT"
    FIXED = "FIXED"

class VoucherStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    EXPIRED = "EXPIRED"

class BlogStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

# === 1. BẢNG USERS (Người dùng & Admin) ===
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)
    gender = Column(String(20), nullable=True)
    birth_date = Column(Date, nullable=True)
    password_hash = Column(String(255), nullable=False)
    
    # Sử dụng Enum cho type và status để kiểm soát dữ liệu cứng
    user_type = Column(Enum(UserType), default=UserType.USER, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    reset_tokens = relationship("PasswordResetToken", back_populates="user")


# === 2. BẢNG PASSWORD_RESET_TOKENS (Lưu OTP Quên mật khẩu) ===
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    email = Column(String(150), nullable=False)
    otp_code = Column(String(255), nullable=False) # Lưu dạng hash để bảo mật
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    is_used = Column(Boolean, default=False)
    reset_token = Column(String(255), nullable=True, unique=True, index=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="reset_tokens")


# === 3. BẢNG PROVINCES (Tỉnh / Thành Phố) ===
class Province(Base):
    __tablename__ = "provinces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(150), nullable=False, unique=True, index=True)
    region = Column(String(50), nullable=True) # Miền Bắc, Miền Trung, Miền Nam
    image = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    places = relationship("Place", back_populates="province")


# === 4. BẢNG PLACES (Địa điểm du lịch thuộc Tỉnh) ===
class Place(Base):
    __tablename__ = "places"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    province_id = Column(UUID(as_uuid=True), ForeignKey("provinces.id"), nullable=False)
    name = Column(String(150), nullable=False)
    slug = Column(String(200), nullable=False, unique=True, index=True)
    category = Column(String(100), nullable=True) # VD: Di tích, Biển, Khu vui chơi
    address = Column(String(255), nullable=True)
    image = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    
    is_featured = Column(Boolean, default=False) # Có hiển thị lên mục Nổi bật không?
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    province = relationship("Province", back_populates="places")
    products = relationship("Product", back_populates="place", cascade="all, delete-orphan")


# === 5. BẢNG PRODUCTS (Sản phẩm / Tour) ===
class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    place_id = Column(UUID(as_uuid=True), ForeignKey("places.id"), nullable=False)
    
    title = Column(String(200), nullable=False)
    slug = Column(String(250), nullable=False, unique=True, index=True)
    price = Column(Numeric(12, 2), nullable=False, default=0) # Cho phép lưu giá tiền lớn
    duration = Column(String(100), nullable=True) # Ví dụ: 3 ngày 2 đêm
    image = Column(Text, nullable=True)
    gallery = Column(JSON, nullable=True) # Danh sách ảnh
    description = Column(Text, nullable=True)
    
    # Các trường nội dung dài
    highlights = Column(Text, nullable=True)
    terms = Column(Text, nullable=True)
    cancellation_policy = Column(Text, nullable=True)
    usage_guide = Column(Text, nullable=True)
    
    category = Column(String(50), nullable=False, default="TOUR")
    is_featured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    place = relationship("Place", back_populates="products")
    ticket_types = relationship("TicketType", back_populates="product", cascade="all, delete-orphan")


# === 6. BẢNG TICKET_TYPES (Gói Dịch Vụ / Loại Vé) ===
class TicketType(Base):
    __tablename__ = "ticket_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    price = Column(Numeric(12, 2), nullable=False, default=0)
    original_price = Column(Numeric(12, 2), nullable=True)
    
    min_quantity = Column(Integer, default=1)
    max_quantity = Column(Integer, default=10)
    
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="ticket_types")


# === 7. BẢNG BANNERS (Quảng cáo / Banner) ===
class Banner(Base):
    __tablename__ = "banners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=False)
    link = Column(String(255), nullable=True)
    position = Column(Enum(BannerPosition), default=BannerPosition.HOME_MAIN, nullable=False)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PricingRule(Base):
    __tablename__ = "pricing_rules"
    __table_args__ = (
        UniqueConstraint("ticket_type_id", "date", name="uq_pricing_rules_ticket_type_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    ticket_type_id = Column(UUID(as_uuid=True), ForeignKey("ticket_types.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    price = Column(Numeric(12, 2), nullable=False, default=0)
    original_price = Column(Numeric(12, 2), nullable=True)
    stock = Column(Integer, nullable=False, default=0)
    status = Column(Enum(PricingStatus), default=PricingStatus.OPEN, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    product_name = Column(String(200), nullable=False)
    user_name = Column(String(120), nullable=False)
    user_avatar = Column(Text, nullable=True)
    rating = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False)
    admin_reply = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Voucher(Base):
    __tablename__ = "vouchers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    discount_type = Column(Enum(DiscountType), default=DiscountType.PERCENT, nullable=False)
    discount_value = Column(Numeric(12, 2), nullable=False)
    min_order_value = Column(Numeric(12, 2), nullable=True)
    max_discount_value = Column(Numeric(12, 2), nullable=True)
    usage_limit = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0, nullable=False)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    status = Column(Enum(VoucherStatus), default=VoucherStatus.ACTIVE, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(250), nullable=False)
    slug = Column(String(280), nullable=False, unique=True, index=True)
    excerpt = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    cover_image = Column(Text, nullable=True)
    author_name = Column(String(120), nullable=True)
    status = Column(Enum(BlogStatus), default=BlogStatus.DRAFT, nullable=False)
    is_featured = Column(Boolean, default=False)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    order_code = Column(String(50), nullable=False, unique=True, index=True)
    payment_code = Column(String(50), nullable=True, unique=True, index=True)

    customer_name = Column(String(120), nullable=False)
    customer_phone = Column(String(30), nullable=False)
    customer_email = Column(String(150), nullable=False)
    customer_address = Column(String(255), nullable=True)

    items = Column(JSON, nullable=False)
    total_amount = Column(Numeric(14, 2), nullable=False, default=0)

    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    payment_method = Column(String(50), default="SEPAY", nullable=False)

    paid_at = Column(DateTime, nullable=True)
    sepay_transaction_id = Column(String(255), nullable=True, unique=True, index=True)
    sepay_reference_code = Column(String(255), nullable=True, unique=True, index=True)
    sepay_content = Column(Text, nullable=True)
    sepay_raw_payload = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    key = Column(String(120), nullable=False, unique=True, index=True)
    value = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentWebhookEvent(Base):
    __tablename__ = "payment_webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    reference_code = Column(String(255), nullable=False, unique=True, index=True)
    transaction_id = Column(String(255), nullable=True, unique=True, index=True)
    order_code = Column(String(50), nullable=True, index=True)
    provider = Column(String(50), nullable=False, default="SEPAY")
    amount = Column(Numeric(14, 2), nullable=True)
    content = Column(Text, nullable=True)
    bank_code = Column(String(32), nullable=True)
    account_number = Column(String(64), nullable=True)
    account_name = Column(String(150), nullable=True)
    status = Column(String(50), nullable=False, default="SUCCESS")
    transaction_time = Column(DateTime, nullable=True)
    raw_payload = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
