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
from app.orders.services import create_order, get_user_orders, get_order, update_order, get_order_items, get_all_orders_admin, update_order_status_admin
from app.products.services import get_product

router = APIRouter(prefix="/api", tags=["orders"])

@router.get("/admin/orders", response_model=List[OrderResponse])
async def get_all_orders(
    db: Session = Depends(get_db),
    user = Depends(JWTBearer())
):
    """Get all orders (Admin only)"""
    if user is None or user['role'] != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorised")
        
    try:
        orders = get_all_orders_admin(db)
        result = []
        for i in orders:
            if isinstance(i.id, uuid.UUID):
                i.id = str(i.id)
            if isinstance(i.user_id, uuid.UUID):
                i.user_id = str(i.user_id)
            for item in i.order_items:
                if isinstance(item.id, uuid.UUID):
                    item.id = str(item.id)
                if isinstance(item.order_id, uuid.UUID):
                    item.order_id = str(item.order_id)
                if isinstance(item.product_id, uuid.UUID):
                    item.product_id = str(item.product_id)
                if isinstance(item.product.id, uuid.UUID):
                    item.product.id = str(item.product.id)
            result.append(i)
        return [OrderResponse.from_orm(order) for order in result]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/admin/orders/{order_id}", response_model=OrderResponse)
async def admin_update_order_status(
    order_id: str,
    status_update: dict,
    db: Session = Depends(get_db),
    user = Depends(JWTBearer())
):
    """Update order status (Admin only)"""
    if user is None or user['role'] != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorised")
        
    try:
        new_status = status_update.get('status')
        order = update_order_status_admin(db, order_id, new_status)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        if isinstance(order.id, uuid.UUID):
            order.id = str(order.id)
        if isinstance(order.user_id, uuid.UUID):
            order.user_id = str(order.user_id)
            
        return order
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/orders", response_model=OrderResponse)
async def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    user = Depends(JWTBearer())
):
    """Create a new order"""
    try:
        # Verify product availability and calculate total
        total_amount = 0
        enriched_items = []
        for item in order.order_items:
            product = get_product(db, item.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product {item.product_id} not found"
                )
            if product.count < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough stock for product {product.name}"
                )
            price = float(product.original_price)
            total_amount += price * item.quantity
            
            # Create enriched item dict with correct price
            item_data = item.model_dump()
            item_data['price'] = price
            enriched_items.append(item_data)

        # Create order with calculated total
        order_data = order.model_dump()
        order_data["total_amount"] = total_amount
        order_data["order_items"] = enriched_items
        user_id = user.get('id')
        db_order = create_order(db, user_id, order_data)
        return db_order
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    db: Session = Depends(get_db),
    user = Depends(JWTBearer())
):
    """Get all orders for the current user"""
    try:
        orders = get_user_orders(db, user.get('id', ''))

        result = []

        for i in orders:
            if isinstance(i.id, uuid.UUID):
                i.id = str(i.id)
            if isinstance(i.user_id, uuid.UUID):
                i.user_id = str(i.user_id)
            for item in i.order_items:
                if isinstance(item.id, uuid.UUID):
                    item.id = str(item.id)
                if isinstance(item.order_id, uuid.UUID):
                    item.order_id = str(item.order_id)
                if isinstance(item.product_id, uuid.UUID):
                    item.product_id = str(item.product_id)
                if isinstance(item.product.id, uuid.UUID):
                    item.product.id = str(item.product.id)
            result.append(i)

        return [OrderResponse.from_orm(order) for order in result]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    order_id: str,
    db: Session = Depends(get_db),
    user = Depends(JWTBearer())
):
    """Get order by ID"""
    try:
        user_id = user.get('id')
        order = get_order(db, user_id, order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        if isinstance(order.id, uuid.UUID):
            order.id = str(order.id)
        if isinstance(order.user_id, uuid.UUID):
            order.user_id = str(order.user_id)
        for item in order.order_items:
            if isinstance(item.id, uuid.UUID):
                item.id = str(item.id)
            if isinstance(item.order_id, uuid.UUID):
                item.order_id = str(item.order_id)
            if isinstance(item.product_id, uuid.UUID):
                item.product_id = str(item.product_id)
            if isinstance(item.product.id, uuid.UUID):
                item.product.id = str(item.product.id)

            print("Items", item.__dict__)

        print("order", order.__dict__)
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
    user = Depends(JWTBearer())
):
    """Update order status"""
    try:
        user_id = user.get('id')
        order = update_order(db, user_id, order_id, status)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        if isinstance(order.id, uuid.UUID):
            order.id = str(order.id)
        if isinstance(order.user_id, uuid.UUID):
            order.user_id = str(order.user_id)
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
    user = Depends(JWTBearer())
):
    """Get items for a specific order"""
    try:
        items = get_order_items(db, order_id)
        if not items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        for item in items:
            if isinstance(item.id, uuid.UUID):
                item.id = str(item.id)
            if isinstance(item.order_id, uuid.UUID):
                item.order_id = str(item.order_id)
        return items
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )