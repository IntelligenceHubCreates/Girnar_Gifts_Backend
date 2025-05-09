from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class OrderItemBase(BaseModel):
    product_id: str
    quantity: int
    price: float

class OrderBase(BaseModel):
    shipping_address: str
    total_amount: float
    status: str = "processing"
    order_items: List[OrderItemBase] = []

class OrderCreate(OrderBase):
    pass

class OrderItemResponse(OrderItemBase):
    id: str
    order_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class OrderResponse(OrderBase):
    id: str
    user_id: str
    order_date: datetime
    order_items: List[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    shipping_address_id: Optional[str] = None 