"""
Bulk product import stub for Girnar Gifts.

Consumes the CSV format documented in MANUAL_STEPS.md:
    sku,title,category,mrp,price,gst_percent,hsn,stock,weight_g,short_desc,tags,image_urls

STUB: the current Product model (app/products/models.py) does not yet have
sku, gst_percent, hsn, weight_g, or a dedicated stock column (Phase 5 adds
these via a new Alembic migration). Until that lands, this script maps what
it can onto the existing columns (name, category, original_price,
amount_discount, count, description, product_image) and skips the rest -
re-run once Phase 5's migration is applied to get full fidelity.

Usage:
    python -m app.scripts.seed_products path/to/products.csv
"""
from __future__ import annotations

import csv
import sys

from app.db import SessionLocal
# Import all model modules so SQLAlchemy can resolve string-based
# relationship() targets on Product/Category (same as alembic/env.py).
from app.orders import models as _orders_models  # noqa: F401
from app.cart import models as _cart_models  # noqa: F401
from app.favorite import models as _favorite_models  # noqa: F401
from app.rating import models as _rating_models  # noqa: F401
from app.users import models as _user_models  # noqa: F401
from app.products.models import Category, Product


def main(csv_path: str) -> None:
    db = SessionLocal()
    try:
        created, skipped = 0, 0
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                title = row["title"].strip()
                existing = db.query(Product).filter(Product.name == title).first()
                if existing:
                    skipped += 1
                    continue

                category = (
                    db.query(Category)
                    .filter(Category.name == row["category"].strip())
                    .first()
                )

                mrp = int(float(row["mrp"]))
                price = int(float(row["price"]))
                image_urls = [u.strip() for u in row.get("image_urls", "").split("|") if u.strip()]

                db.add(Product(
                    name=title,
                    category_id=category.id if category else None,
                    category=row["category"].strip(),
                    description=row.get("short_desc", ""),
                    original_price=mrp,
                    amount_discount=max(mrp - price, 0),
                    count=int(row.get("stock", 0) or 0),
                    product_image=[{"url": u} for u in image_urls],
                    is_active=True,
                ))
                created += 1
        db.commit()
        print(f"Created {created} products, skipped {skipped} existing.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.scripts.seed_products path/to/products.csv", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
