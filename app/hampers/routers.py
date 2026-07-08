# app/hampers/routers.py
"""
Build-your-own-hamper: a customer picks several existing products and a
quantity for each; this endpoint prices the picks (same discount math as
checkout) and materializes ONE real Product row flagged is_custom_bundle
so it flows through the existing cart/checkout/order pipeline unchanged,
while storefront listings (see app/products/routers.py) filter it out.
"""
from __future__ import annotations

import math
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.products.models import Product
from app.users.utils import JWTBearer

hamper_router = APIRouter(prefix="/api/hampers", tags=["Hampers"])

HAMPER_FEE       = 49.0
MAX_HAMPER_ITEMS = 30


class HamperItemIn(BaseModel):
    product_id: str
    quantity:   int = Field(1, ge=1, le=50)


class HamperCreateRequest(BaseModel):
    name:  Optional[str] = None
    items: List[HamperItemIn]


def _unit_price(product: Product) -> float:
    orig = float(product.original_price or 0)
    amt  = float(product.amount_discount or 0)
    pct  = float(product.percentage_discount or 0)
    if amt > 0:
        unit = orig - amt
    elif pct > 0:
        unit = float(math.floor(orig - orig * pct / 100 + 0.5))
    else:
        unit = orig
    return max(0.0, unit)


def _cover_image(product: Product) -> Optional[str]:
    images = product.product_image
    if not isinstance(images, list) or not images:
        return None
    first = images[0]
    if isinstance(first, str):
        return first
    if isinstance(first, dict):
        return first.get("url") or first.get("secure_url")
    return None


@hamper_router.post("", status_code=201)
async def create_hamper(
    payload: HamperCreateRequest,
    user=Depends(JWTBearer()),
    session: Session = Depends(get_db),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Add at least one item to your hamper")

    merged: dict[str, int] = {}
    for it in payload.items:
        merged[it.product_id] = merged.get(it.product_id, 0) + it.quantity

    if len(merged) > MAX_HAMPER_ITEMS:
        raise HTTPException(status_code=400, detail=f"A hamper can include at most {MAX_HAMPER_ITEMS} different items")

    lines: list[dict] = []
    subtotal = 0.0
    cover_image: Optional[str] = None

    for pid, qty in merged.items():
        try:
            puid = UUID(pid)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid product id: {pid}")

        product = session.query(Product).filter(Product.id == puid, Product.is_active.is_(True)).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product not found: {pid}")
        if product.is_custom_bundle:
            raise HTTPException(status_code=400, detail="A hamper can't contain another hamper")
        if product.count < qty:
            raise HTTPException(status_code=400, detail=f"Only {product.count} left of {product.name}")

        unit = _unit_price(product)
        subtotal += unit * qty
        img = _cover_image(product)
        if not cover_image and img:
            cover_image = img

        lines.append({
            "product_id": str(product.id),
            "name":       product.name,
            "quantity":   qty,
            "unit_price": unit,
            "image":      img,
        })

    total = round(subtotal + HAMPER_FEE, 2)
    item_count = sum(l["quantity"] for l in lines)
    name = (payload.name or "").strip() or f"Custom Hamper ({item_count} item{'s' if item_count != 1 else ''})"
    contents_desc = "; ".join(f"{l['quantity']}x {l['name']}" for l in lines)

    bundle = Product(
        name=name,
        category="Personalised Gifts",
        description=f"A custom hamper you built: {contents_desc}.",
        details=[f"{l['quantity']}x {l['name']}" for l in lines],
        original_price=int(round(total)),
        count=1,
        product_image=[cover_image] if cover_image else [],
        is_active=True,
        is_custom_bundle=True,
        bundle_items=lines,
    )
    session.add(bundle)
    session.commit()
    session.refresh(bundle)

    return {
        "id":         str(bundle.id),
        "name":       bundle.name,
        "price":      total,
        "subtotal":   round(subtotal, 2),
        "hamper_fee": HAMPER_FEE,
        "image":      cover_image,
        "items":      lines,
    }
