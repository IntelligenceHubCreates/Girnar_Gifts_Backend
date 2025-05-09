from datetime import datetime
from app.models import Base
from sqlalchemy import Column, ForeignKey, Integer, String, DECIMAL, DateTime, func
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.orm import relationship
import uuid
from sqlalchemy.dialects.postgresql import UUID
from typing import List
from app.users.models import Users
from app.products.models import Product

class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    total_amount = Column(DECIMAL(20, 2), nullable=False)
    status = Column(String(50), nullable=False)
    shipping_address = Column(String(500), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    user = relationship("Users", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(DECIMAL(20, 2), nullable=False)
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")