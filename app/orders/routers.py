from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.orders.models import Order, OrderItem
from app.orders.schemas import OrderCreate, OrderResponse, OrderItemResponse
from app.users.models import Users
from app.products.models import Product
from app.users.utils import get_current_user
from typing import List
import uuid

router = APIRouter(prefix='/api/orders')

@router.post("", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        user = await get_current_user(request, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please log in first."
            )

        # Validate all products exist and have sufficient stock
        for item in order_data.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {item.product_id} not found"
                )
            if product.stock < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for product {product.name}. Available: {product.stock}, Requested: {item.quantity}"
                )

        # Create the order
        new_order = Order(
            id=uuid.uuid4(),
            user_id=user.get("id"),
            total_amount=order_data.total_amount,
            status=order_data.status,
            shipping_address=order_data.shipping_address
        )
        db.add(new_order)
        db.flush()  # This will generate the order ID without committing

        # Create order items and update product stock
        order_items = []
        for item in order_data.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            
            # Create order item
            order_item = OrderItem(
                id=uuid.uuid4(),
                order_id=new_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price
            )
            db.add(order_item)
            order_items.append(order_item)
            
            # Update product stock
            product.stock -= item.quantity

        db.commit()
        db.refresh(new_order)
        
        # Create response with proper structure
        response = OrderResponse(
            id=new_order.id,
            user_id=new_order.user_id,
            order_date=new_order.order_date,
            total_amount=new_order.total_amount,
            status=new_order.status,
            shipping_address=new_order.shipping_address,
            items=[
                OrderItemResponse(
                    id=item.id,
                    order_id=item.order_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price=item.price
                ) for item in order_items
            ]
        )
        return response
    except HTTPException as he:
        db.rollback()
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create order: {str(e)}"
        )

@router.get("/", response_model=List[OrderResponse])
async def get_user_orders(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        user = await get_current_user(request, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please log in first."
            )
        
        orders = db.query(Order).filter(Order.user_id == user.id).all()
        return [
            OrderResponse(
                id=order.id,
                user_id=order.user_id,
                order_date=order.order_date,
                total_amount=order.total_amount,
                status=order.status,
                shipping_address=order.shipping_address,
                items=[
                    OrderItemResponse(
                        id=item.id,
                        order_id=item.order_id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        price=item.price
                    ) for item in order.order_items
                ]
            ) for order in orders
        ]
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch orders: {str(e)}"
        )

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_details(
    order_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        user = await get_current_user(request, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please log in first."
            )
        
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == user.id
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
            
        return OrderResponse(
            id=order.id,
            user_id=order.user_id,
            order_date=order.order_date,
            total_amount=order.total_amount,
            status=order.status,
            shipping_address=order.shipping_address,
            items=[
                OrderItemResponse(
                    id=item.id,
                    order_id=item.order_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price=item.price
                ) for item in order.order_items
            ]
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch order details: {str(e)}"
        ) 