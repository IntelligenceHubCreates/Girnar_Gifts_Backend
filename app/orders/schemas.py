from pydantic import BaseModel, UUID4
from typing import List, Optional
from datetime import datetime

class OrderItemBase(BaseModel):
    product_id: UUID4
    quantity: int
    price: float

class OrderBase(BaseModel):
    shipping_address: str
    total_amount: float
    status: str = "pending"
    items: List[OrderItemBase]

class OrderCreate(OrderBase):
    pass

class OrderItemResponse(OrderItemBase):
    id: UUID4
    order_id: UUID4

    class Config:
        from_attributes = True

class OrderResponse(OrderBase):
    id: UUID4
    user_id: UUID4
    order_date: datetime
    items: List[OrderItemResponse]

    class Config:
        from_attributes = True 