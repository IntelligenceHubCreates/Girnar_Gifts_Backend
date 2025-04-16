from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.orders.models import Order, OrderItem
from app.orders.schemas import OrderCreate, OrderResponse, OrderItemResponse
from app.users.models import Users
from app.products.models import Product
from app.users.utils import get_current_user, JWTBearer
from typing import List
import uuid
from pydantic import BaseModel
from datetime import datetime
from app.orders.services import create_order, get_user_orders, get_order, update_order, get_order_items
from app.products.services import get_product

router = APIRouter(prefix="/api", tags=["orders"])

@router.post("/orders/", response_model=OrderResponse)
async def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    token: str = Depends(JWTBearer())
):
    """Create a new order"""
    try:
        # Verify product availability and calculate total
        total_amount = 0
        for item in order.items:
            product = get_product(db, item.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product {item.product_id} not found"
                )
            if product.stock < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough stock for product {product.name}"
                )
            total_amount += product.price * item.quantity

        # Create order with calculated total
        order_data = order.model_dump()
        order_data["total_amount"] = total_amount
        db_order = create_order(db, order_data)
        return db_order
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/orders/", response_model=List[OrderResponse])
async def get_orders(
    db: Session = Depends(get_db),
    token: str = Depends(JWTBearer())
):
    """Get all orders for the current user"""
    try:
        orders = get_user_orders(db, token)
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    order_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(JWTBearer())
):
    """Get order by ID"""
    try:
        order = get_order(db, order_id, token)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        return order
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/orders/{order_id}", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    status: str,
    db: Session = Depends(get_db),
    token: str = Depends(JWTBearer())
):
    """Update order status"""
    try:
        order = update_order(db, order_id, status, token)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        return order
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/orders/{order_id}/items", response_model=List[OrderItemResponse])
async def get_items_for_order(
    order_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(JWTBearer())
):
    """Get items for a specific order"""
    try:
        items = get_order_items(db, order_id, token)
        if not items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        return items
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 