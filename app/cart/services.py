from sqlalchemy.orm import Session, joinedload
from app.cart.models import Cart, CartItem
from app.cart.schemas import CartItemCreate, CartItemUpdate
from app.products.models import Product
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import desc

def get_or_create_cart(db: Session, user_id: str) -> Cart:
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart

def get_cart(db: Session, user_id: str) -> Optional[Cart]:
    # First get the cart
    cart = db.query(Cart)\
        .filter(Cart.user_id == user_id)\
        .first()
    
    if not cart:
        return None
    
    # Then get the cart items with sorting
    cart_items = db.query(CartItem)\
        .filter(CartItem.cart_id == cart.id)\
        .order_by(desc(CartItem.created_at))\
        .all()
    
    # Set the sorted cart items
    cart.cart_items = cart_items
    
    # Load the products for each cart item
    for item in cart.cart_items:
        item.product = db.query(Product).filter(Product.id == item.product_id).first()
    
    return cart

def add_to_cart(db: Session, user_id: str, item: CartItemCreate) -> CartItem:
    cart = get_or_create_cart(db, user_id)
    
    # Get the product and check available quantity
    product = db.query(Product).filter(Product.id == item.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if requested quantity is available
    if product.count < item.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {product.count} items available in stock"
        )
    
    # Check if product already exists in cart
    existing_item = db.query(CartItem)\
        .filter(CartItem.cart_id == cart.id, CartItem.product_id == item.product_id)\
        .first()
    
    if existing_item:
        # Check if total quantity (existing + new) is available
        if product.count < (existing_item.quantity + item.quantity):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only {product.count - existing_item.quantity} more items available in stock"
            )
        existing_item.quantity += item.quantity
        db.commit()
        db.refresh(existing_item)
        return existing_item
    
    # Create new cart item
    cart_item = CartItem(
        cart_id=cart.id,
        product_id=item.product_id,
        quantity=item.quantity
    )
    
    # Decrease product count
    
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    return cart_item

def update_cart_item(db: Session, user_id: str, item_id: str, item_update: CartItemUpdate) -> Optional[CartItem]:
    cart = get_cart(db, user_id)
    if not cart:
        return None
        
    cart_item = db.query(CartItem)\
        .filter(CartItem.id == item_id, CartItem.cart_id == cart.id)\
        .first()
    
    if not cart_item:
        return None
        
    cart_item.quantity = item_update.quantity
    db.commit()
    db.refresh(cart_item)
    return cart_item

def remove_from_cart(db: Session, user_id: str, item_id: str) -> bool:
    cart = get_cart(db, user_id)
    if not cart:
        return False
        
    cart_item = db.query(CartItem)\
        .filter(CartItem.id == item_id, CartItem.cart_id == cart.id)\
        .first()
    
    if not cart_item:
        return False
        
    db.delete(cart_item)
    db.commit()
    return True

def clear_cart(db: Session, user_id: str) -> bool:
    cart = get_cart(db, user_id)
    if not cart:
        return False
        
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    return True