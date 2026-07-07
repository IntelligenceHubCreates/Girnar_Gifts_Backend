"""
Idempotent Girnar Gifts category taxonomy sync.

Usage:
    python -m app.scripts.seed_categories

Safe to re-run: adds any category in CATEGORIES that's missing (matched by
slug), and retires any category in RETIRED_SLUGS - hard-deleted if no
products reference it, or just deactivated (is_active=False) with a warning
if products do, so real product data is never silently orphaned.
"""
from __future__ import annotations

from app.db import SessionLocal
# Import all model modules so SQLAlchemy can resolve string-based
# relationship() targets on Product/Category (same as alembic/env.py).
from app.orders import models as _orders_models  # noqa: F401
from app.cart import models as _cart_models  # noqa: F401
from app.favorite import models as _favorite_models  # noqa: F401
from app.rating import models as _rating_models  # noqa: F401
from app.users import models as _user_models  # noqa: F401
from app.products.models import Category, Product

CATEGORIES = [
    {"name": "Personalised Gifts", "slug": "personalised-gifts", "emoji": "\U0001F381", "sort_order": 1},
    {"name": "Gift Hampers", "slug": "gift-hampers", "emoji": "\U0001F9FA", "sort_order": 2},
    {"name": "Festive & Occasion", "slug": "festive-occasion", "emoji": "\U0001F386", "sort_order": 3},
    {"name": "Stationery", "slug": "stationery", "emoji": "\U0000270F", "sort_order": 4},
    {"name": "Bags & Pouches", "slug": "bags-pouches", "emoji": "\U0001F45D", "sort_order": 5},
    {"name": "Bottles", "slug": "bottles", "emoji": "\U0001F9F4", "sort_order": 6},
    {"name": "Toys", "slug": "toys", "emoji": "\U0001F9F8", "sort_order": 7},
]

# Categories retired from the taxonomy above - kept here (not just deleted
# from history) so sync_categories() below knows what to remove from an
# already-seeded database instead of leaving them orphaned as stale rows.
RETIRED_SLUGS = ["corporate-gifts", "home-decor", "chocolates-sweets", "flowers-plants"]


def main() -> None:
    db = SessionLocal()
    try:
        created = 0
        for cat in CATEGORIES:
            existing = db.query(Category).filter(Category.slug == cat["slug"]).first()
            if existing:
                continue
            db.add(Category(**cat, is_active=True))
            created += 1
        db.commit()
        print(f"Seeded {created} new categories ({len(CATEGORIES) - created} already existed).")

        deleted, deactivated = 0, 0
        for slug in RETIRED_SLUGS:
            cat = db.query(Category).filter(Category.slug == slug).first()
            if not cat:
                continue
            product_count = db.query(Product).filter(Product.category_id == cat.id).count()
            if product_count == 0:
                db.delete(cat)
                deleted += 1
            else:
                cat.is_active = False
                deactivated += 1
                print(f"  WARNING: '{cat.name}' ({slug}) has {product_count} product(s) - "
                      f"deactivated instead of deleted. Move those products to a new "
                      f"category, then re-run this script to remove it for good.")
        db.commit()
        if deleted or deactivated:
            print(f"Retired categories: {deleted} deleted, {deactivated} deactivated.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
