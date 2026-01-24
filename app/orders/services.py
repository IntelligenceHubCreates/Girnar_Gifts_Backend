from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from app.orders.models import Order, OrderItem
from app.orders.schemas import OrderCreate, OrderUpdate
from app.products.models import Product
from sqlalchemy.orm import joinedload

def create_order(db: Session, user_id: str, order: dict) -> Order:
    """Create a new order"""
    try:
        db_order = Order(
            user_id=user_id,
            shipping_address=order['shipping_address'],
            total_amount=order['total_amount'],
            status=order['status'],
            order_date=datetime.utcnow()
        )
        db.add(db_order)
        db.flush()  # Get the order ID without committing

        # Create order items
        for item in order['order_items']:
            db_item = OrderItem(
                order_id=db_order.id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.add(db_item)

        db.commit()
        db.refresh(db_order)
        return db_order
    except Exception as e:
        db.rollback()
        raise e

def get_user_orders(db: Session, user_id: str) -> List[Order]:
    """Get all orders for user"""
    return db.query(Order).filter(Order.user_id == user_id).all()

def get_order(db: Session, user_id: str, order_id: str) -> Order:
    """Get specific order for user"""
    return db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == user_id
    ).options(
        joinedload(Order.order_items).joinedload(OrderItem.product)
    ).first()

def update_order(
    db: Session,
    user_id: str,
    order_id: str,
    order: OrderUpdate
) -> Order:
    """Update order"""
    try:
        db_order = get_order(db, user_id, order_id)
        if not db_order:
            return None
        
        for key, value in order.model_dump(exclude_unset=True).items():
            setattr(db_order, key, value)
        
        db_order.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_order)
        return db_order
    except Exception as e:
        db.rollback()
        raise e

def get_order_items(db: Session, order_id: str) -> List[OrderItem]:
    """Get all items for an order"""
    return db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

def get_all_orders_admin(db: Session) -> List[Order]:
    """Get all orders for admin"""
    return db.query(Order).options(
        joinedload(Order.order_items).joinedload(OrderItem.product)
    ).all()

def update_order_status_admin(
    db: Session,
    order_id: str,
    status: str
) -> Order:
    """Update order status for admin"""
    try:
        db_order = db.query(Order).filter(Order.id == order_id).first()
        if not db_order:
            return None
        
        db_order.status = status
        db_order.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_order)
        return db_order
    except Exception as e:
        db.rollback()
        raise e