# app/payments/router.py
from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime
from typing import List, Optional

import razorpay
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Session

from app.db import Base, get_db
from app.settings import settings
from app.users.utils import JWTBearer
from app.orders.models import Order, OrderItem
from app.orders.services import create_order as svc_create_order
from app.products.models import Product

payment_router = APIRouter(prefix="/api/payments", tags=["Payments"])


def get_razorpay_client() -> razorpay.Client:
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(status_code=503, detail="Payment service not configured.")
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


# ── ORM ───────────────────────────────────────────────────────────────────

class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    razorpay_order_id   = Column(String(100), unique=True, nullable=False, index=True)
    razorpay_payment_id = Column(String(100), nullable=True, index=True)
    razorpay_signature  = Column(String(300), nullable=True)
    amount              = Column(Integer, nullable=False)   # paise
    currency            = Column(String(10), default="INR")
    status              = Column(String(30), default="created")
    cart_snapshot       = Column(JSON, nullable=True)
    shipping_address    = Column(JSON, nullable=True)
    is_verified         = Column(Boolean, default=False)
    created_at          = Column(DateTime(timezone=True), default=datetime.utcnow)
    paid_at             = Column(DateTime(timezone=True), nullable=True)


# ── Schemas ───────────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    amount: int
    cart_items: List[dict]
    shipping_address: dict
    coupon_code: Optional[str] = None      # ← NEW
    gift_message: Optional[str] = None     # ← NEW
    notes: Optional[dict] = None

class CreateOrderResponse(BaseModel):
    razorpay_order_id: str
    amount: int
    currency: str
    key_id: str

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id:   str
    razorpay_payment_id: str
    razorpay_signature:  str

class VerifyPaymentResponse(BaseModel):
    success:    bool
    payment_id: str
    order_id:   str
    message:    str


# ── Endpoints ─────────────────────────────────────────────────────────────

@payment_router.post("/create-order", response_model=CreateOrderResponse)
async def create_payment_order(
    body: CreateOrderRequest,
    session: Session = Depends(get_db),
    user=Depends(JWTBearer()),
):
    import math
    from app.coupons.services import evaluate_coupon, CouponError

    DELIVERY_FEE            = 49.0
    FREE_DELIVERY_THRESHOLD = 499.0

    if not body.cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # ── Recompute subtotal from REAL product prices (never trust client) ──
    subtotal = 0.0
    for item in body.cart_items:
        product = session.query(Product).filter(Product.id == item.get("product_id")).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product not found: {item.get('product_id')}")
        if not getattr(product, "is_active", True):
            raise HTTPException(status_code=400, detail=f"{product.name} is no longer available")
        qty = int(item.get("quantity", 1))
        if qty < 1:
            raise HTTPException(status_code=400, detail="Invalid quantity")
        if product.count < qty:
            raise HTTPException(status_code=400, detail=f"Only {product.count} left for {product.name}")

        orig = float(product.original_price or 0)
        amt  = float(getattr(product, "amount_discount", 0) or 0)
        pct  = float(getattr(product, "percentage_discount", 0) or 0)
        if amt > 0:   unit = orig - amt
        elif pct > 0: unit = float(math.floor(orig - orig * pct / 100 + 0.5))
        else:         unit = orig
        subtotal += max(0.0, unit) * qty

    # ── Coupon (server-validated) ──
    discount = 0.0
    coupon_code_norm = None
    if body.coupon_code:
        try:
            coupon_obj, discount = evaluate_coupon(session, body.coupon_code, subtotal)
            coupon_code_norm = coupon_obj.code
        except CouponError as ce:
            raise HTTPException(status_code=400, detail=f"Coupon: {ce.message}")

    delivery = 0.0 if subtotal >= FREE_DELIVERY_THRESHOLD else DELIVERY_FEE
    total_rupees = max(0.0, subtotal - discount + delivery)
    amount_paise = int(round(total_rupees * 100))

    if amount_paise <= 0:
        raise HTTPException(status_code=400, detail="Invalid order total")

    client = get_razorpay_client()
    try:
        rz_order = client.order.create({
            "amount": amount_paise, "currency": "INR",
            "receipt": f"{settings.razorpay_receipt_prefix}{uuid.uuid4().hex[:12]}",
            "payment_capture": 1,
            "notes": {"source": settings.brand_name},
        })
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Razorpay error: {str(e)}")

    # Snapshot everything verify needs to build the real order
    snapshot = {
        "items":        body.cart_items,
        "coupon_code":  coupon_code_norm,
        "gift_message": (body.gift_message or "").strip()[:500] or None,
        "subtotal":     subtotal,
        "discount":     discount,
        "delivery":     delivery,
        "total":        total_rupees,
    }

    session.add(PaymentOrder(
        user_id=uuid.UUID(str(user["id"])) if user and user.get("id") else None,
        razorpay_order_id=rz_order["id"],
        amount=amount_paise,
        currency="INR",
        status="created",
        cart_snapshot=snapshot,                 # ← now structured, not just items
        shipping_address=body.shipping_address,
    ))
    session.commit()

    return CreateOrderResponse(
        razorpay_order_id=rz_order["id"], amount=amount_paise,
        currency="INR", key_id=settings.razorpay_key_id,
    )

@payment_router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(
    body: VerifyPaymentRequest,
    session: Session = Depends(get_db),
    user=Depends(JWTBearer()),
):
    order = session.query(PaymentOrder).filter(
        PaymentOrder.razorpay_order_id == body.razorpay_order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.is_verified:
        return VerifyPaymentResponse(
            success=True,
            payment_id=order.razorpay_payment_id,
            order_id=str(order.id),
            message="Already verified",
        )

    expected = hmac.new(
        settings.razorpay_key_secret.encode(),
        f"{body.razorpay_order_id}|{body.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, body.razorpay_signature):
        order.status = "failed"
        session.commit()
        raise HTTPException(status_code=400, detail="Invalid payment signature.")

    order.razorpay_payment_id = body.razorpay_payment_id
    order.razorpay_signature  = body.razorpay_signature
    order.status              = "paid"
    order.is_verified         = True
    order.paid_at             = datetime.utcnow()
    session.commit()

    # ── Create the real Order exactly once (idempotent on payment id) ──
    existing = session.query(Order).filter(
        Order.razorpay_payment_id == body.razorpay_payment_id
    ).first()
    if existing:
        return VerifyPaymentResponse(success=True, payment_id=body.razorpay_payment_id,
                                     order_id=str(existing.id), message="Already created")

    snap  = order.cart_snapshot or {}
    items = snap.get("items", []) if isinstance(snap, dict) else (snap or [])
    addr  = order.shipping_address or {}
    uid   = str(order.user_id) if order.user_id else None

    order_items_data = []
    for it in items:
        order_items_data.append({
            "product_id": it.get("product_id", ""),
            "quantity":   int(it.get("quantity", 1)),
            "price":      float(it.get("price", 0)),   # display; server total already authoritative
            "color":      it.get("color")     or None,
            "color_hex":  it.get("color_hex") or None,
            "image":      it.get("image")     or None,
        })

    shipping_str = (f"{addr.get('fullName','')}, {addr.get('addressLine1','')}, "
                    f"{addr.get('city','')}, {addr.get('state','')} - {addr.get('pincode','')}")

    order_data = {
        "shipping_address": shipping_str,
        "total_amount":     float(snap.get("total", order.amount / 100)),  # server total
        "subtotal":         snap.get("subtotal"),
        "discount_amount":  snap.get("discount") or 0,
        "delivery_fee":     snap.get("delivery") or 0,
        "coupon_code":      snap.get("coupon_code"),
        "gift_message":     snap.get("gift_message"),
        "status":           "confirmed",
        "order_items":      order_items_data,
    }

    try:
        db_order = svc_create_order(session, uid, order_data)  # this now redeems coupon (see note)
        db_order.razorpay_payment_id = body.razorpay_payment_id
        # ── Deduct stock, once, in the paid transaction ──
        for it in items:
            p = session.query(Product).filter(Product.id == it.get("product_id")).first()
            if p:
                p.count = max(0, (p.count or 0) - int(it.get("quantity", 1)))
        session.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Order creation failed: {str(e)}")

    return VerifyPaymentResponse(
        success=True, payment_id=body.razorpay_payment_id,
        order_id=str(db_order.id), message="Payment verified & order created",
    )


@payment_router.get("/order/{razorpay_order_id}")
async def get_order_status(
    razorpay_order_id: str,
    session: Session = Depends(get_db),
    user=Depends(JWTBearer()),
):
    order = session.query(PaymentOrder).filter(
        PaymentOrder.razorpay_order_id == razorpay_order_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "status":              order.status,
        "is_verified":         order.is_verified,
        "amount":              order.amount / 100,
        "razorpay_payment_id": order.razorpay_payment_id,
        "paid_at":             order.paid_at,
    }


@payment_router.post("/webhook")
async def razorpay_webhook(request_body: dict, session: Session = Depends(get_db)):
    event    = request_body.get("event", "")
    entity   = request_body.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = entity.get("order_id")
    if not order_id:
        return {"status": "ok"}
    order = session.query(PaymentOrder).filter(
        PaymentOrder.razorpay_order_id == order_id
    ).first()
    if order:
        if event == "payment.captured" and not order.is_verified:
            order.status              = "paid"
            order.razorpay_payment_id = entity.get("id")
            order.is_verified         = True
            order.paid_at             = datetime.utcnow()
        elif event == "payment.failed":
            order.status = "failed"
        session.commit()
    return {"status": "ok"}


# ── Create order after payment ────────────────────────────────────────────

# @payment_router.post("/create-order-after-payment/{razorpay_order_id}")
# async def create_order_after_payment(
#    razorpay_order_id: str,
#    session: Session = Depends(get_db),
#    user=Depends(JWTBearer()),
#):
#    payment = session.query(PaymentOrder).filter(
#        PaymentOrder.razorpay_order_id == razorpay_order_id,
#        PaymentOrder.is_verified == True,
#    ).first()

#    if not payment:
#        raise HTTPException(status_code=404, detail="Verified payment not found")

    # Idempotent check — column now exists (migration 004).
#    existing = session.query(Order).filter(
#        Order.razorpay_payment_id == payment.razorpay_payment_id
#    ).first()
#    if existing:
#        return _format_order(existing)

#    addr    = payment.shipping_address or {}
#    items   = payment.cart_snapshot    or []
#    user_id = str(user["id"]) if user and user.get("id") else None

#    order_items_data = []
#    total_amount     = 0

#    for item in items:
#        price    = float(item.get("price",    0))
#        quantity = int(item.get("quantity",   1))
#        total_amount += price * quantity

#        order_items_data.append({
#            "product_id": item.get("product_id", ""),
#            "quantity":   quantity,
#            "price":      price,
            # FIX: pass color fields from cart_snapshot into the order item
            # cart_snapshot was saved with full payload including color/color_hex/image
#            "color":      item.get("color")     or None,
#            "color_hex":  item.get("color_hex") or None,
#            "image":      item.get("image")     or None,
#        })

#    shipping_str = (
#        f"{addr.get('fullName',     '')}, "
#        f"{addr.get('addressLine1', '')}, "
#        f"{addr.get('city',         '')}, "
#        f"{addr.get('state',        '')} - "
#        f"{addr.get('pincode',      '')}"
#   )

#    order_data = {
#        "shipping_address": shipping_str,
#        "total_amount":     payment.amount / 100,
#        "payment_method":   "Razorpay",
#        "payment_status":   "paid",
#        "status":           "confirmed",
#        "order_items":      order_items_data,   # now includes color/color_hex/image
#    }

#    try:
#        db_order = svc_create_order(session, user_id, order_data)
#    except Exception as e:
#        raise HTTPException(status_code=500, detail=f"Order creation failed: {str(e)}")

    # Link order → payment so the admin panel shows "Paid".
#    db_order.razorpay_payment_id = payment.razorpay_payment_id
#    session.commit()
#    session.refresh(db_order)

#    return _format_order(db_order)

@payment_router.get("/order-by-payment/{razorpay_payment_id}")
async def get_order_by_payment(
    razorpay_payment_id: str,
    session: Session = Depends(get_db),
    user=Depends(JWTBearer()),
):
    if hasattr(Order, 'razorpay_payment_id'):
        order = session.query(Order).filter(
            Order.razorpay_payment_id == razorpay_payment_id
        ).first()
        if order:
            return _format_order(order)

    payment = session.query(PaymentOrder).filter(
        PaymentOrder.razorpay_payment_id == razorpay_payment_id
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    addr = payment.shipping_address or {}
    return {
        "id":                    str(payment.id),
        "status":                "confirmed" if payment.is_verified else "pending",
        "amount_paid":           payment.amount / 100,
        "payment_method":        "Razorpay",
        "razorpay_payment_id":   payment.razorpay_payment_id,
        "shipping_name":         addr.get("fullName", ""),
        "shipping_city":         addr.get("city", ""),
        "items":                 payment.cart_snapshot or [],
        "created_at":            payment.created_at.isoformat() if payment.created_at else None,
        "tracking_events":       [],
    }


def _format_order(order: Order) -> dict:
    items = []
    for oi in getattr(order, 'order_items', []):
        items.append({
            "product_id": str(getattr(oi, 'product_id', '')),
            "name":       getattr(oi.product, 'name', 'Product') if hasattr(oi, 'product') and oi.product else 'Product',
            "price":      float(getattr(oi, 'price', 0)),
            "quantity":   int(getattr(oi, 'quantity', 1)),
            "color":      getattr(oi, 'color',     None),
            "color_hex":  getattr(oi, 'color_hex', None),
        })

    addr = getattr(order, 'shipping_address', '') or ''
    return {
        "id":                    str(order.id),
        "status":                getattr(order, 'status', 'confirmed'),
        "amount_paid":           float(getattr(order, 'total_amount', 0)),
        "payment_method":        getattr(order, 'payment_method', 'Razorpay'),
        "razorpay_payment_id":   getattr(order, 'razorpay_payment_id', None),
        "shipping_name":         addr.split(',')[0].strip() if addr else '',
        "shipping_city":         addr.split(',')[-2].strip() if ',' in addr else '',
        "shipping_state":        '',
        "shipping_address":      addr,
        "shipping_pincode":      addr.split('-')[-1].strip() if '-' in addr else '',
        "shipping_phone":        '',
        "courier_name":          getattr(order, 'courier_name', None),
        "awb_number":            getattr(order, 'awb_number', None),
        "items":                 items,
        "created_at":            order.created_at.isoformat() if order.created_at else None,
        "estimated_delivery":    None,
        "delivered_at":          getattr(order, 'delivered_at', None),
        "tracking_events":       getattr(order, 'tracking_events', []) or [],
    }