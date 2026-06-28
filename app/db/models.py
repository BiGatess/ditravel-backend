import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, Enum, Numeric, JSON
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

# === 1. BẢNG USERS (Người dùng & Admin) ===
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
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
    is_used = Column(Boolean, default=False)
    
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
