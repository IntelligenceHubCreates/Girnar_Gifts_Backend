import uuid
from sqlalchemy.dialects.postgresql import UUID, JSON
from app.models import Base
from datetime import datetime
from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, Date, text
from pydantic import BaseModel
from typing import Optional

# SQLAlchemy model
class Product(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'), index=True)
    uid = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'), index=True)
    name = Column(String(100), nullable=False, index=True)
    category = Column(String(30), index=True)
    original_price = Column(DECIMAL(20, 2), nullable=False)
    description = Column(String(300), nullable=False, index=True)
    count = Column(Integer, nullable=False)
    percentage_discount = Column(Integer, nullable=False)
    offer_expiration_date = Column(Date, default=datetime.utcnow)
    product_image = Column(JSON, nullable=False, default=[]) 
    date_published = Column(DateTime, default=datetime.utcnow)

# Pydantic schemas
class ProductBase(BaseModel):
    name: str
    category: str
    original_price: float
    description: str
    count: int
    percentage_discount: float
    offer_expiration_date: Optional[datetime] = None
    product_image: list
    date_published: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes=True

class ProductIn(BaseModel):
    name: str
    category: str
    original_price: float
    description: str
    count: int
    percentage_discount: float
    offer_expiration_date: Optional[datetime] = None
    product_image: list
    date_published: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes=True


