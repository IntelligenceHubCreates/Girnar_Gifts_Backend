from datetime import datetime
import uuid
from app.models import Base
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, func, text, DateTime
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import UUID

class Users(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True, unique=True)
    email = Column(String, nullable=False, unique=True)
    name = Column(String(255))
    phone = Column(String(20))
    confirmed = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    hashed_password = Column(String, nullable=True, unique=False)  # Made nullable for Google users
    role = Column(Integer, nullable=False, unique=False)
    google_id = Column(String, nullable=True, unique=True)  # Google ID
    google_id_token = Column(String, nullable=True)  # Google ID token
    google_access_token = Column(String, nullable=True)  # Google access token
    profile_image = Column(String, nullable=True)  # Profile image URL
    tokens = relationship("UserTokens", back_populates="user")
    orders = relationship("Order", back_populates="user")
    addresses = relationship("UserAddress", back_populates="user")
    cart = relationship("Cart", back_populates="user", uselist=False)

class UserAddress(Base):
    __tablename__ = "user_addresses"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255))
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    user = relationship("Users", back_populates="addresses")

class UserTokens(Base):
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, index=True, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    extra = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    user = relationship("Users", back_populates="tokens")

class UserBase(BaseModel):
    email: str
    created_at: datetime

    class Config:
        from_attributes = True
