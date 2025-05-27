from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.products.schemas import ProductBase

class CartItemBase(BaseModel):
    product_id: str
    quantity: int

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(BaseModel):
    quantity: int

class CartItemResponse(CartItemBase):
    id: str
    cart_id: str
    product: ProductBase

    class Config:
        from_attributes = True

class CartResponse(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime]
    cart_items: List[CartItemResponse]

    class Config:
        from_attributes = True