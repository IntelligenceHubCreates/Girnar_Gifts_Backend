"""
Idempotent Girnar Gifts category taxonomy seed.

Usage:
    python -m app.scripts.seed_categories

Safe to re-run: existing categories (matched by slug) are left untouched.
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
from app.products.models import Category

CATEGORIES = [
    {"name": "Personalised Gifts", "slug": "personalised-gifts", "emoji": "\U0001F381", "sort_order": 1},
    {"name": "Gift Hampers", "slug": "gift-hampers", "emoji": "\U0001F9FA", "sort_order": 2},
    {"name": "Festive & Occasion", "slug": "festive-occasion", "emoji": "\U0001F386", "sort_order": 3},
    {"name": "Corporate Gifts", "slug": "corporate-gifts", "emoji": "\U0001F4BC", "sort_order": 4},
    {"name": "Home & Decor", "slug": "home-decor", "emoji": "\U0001F3E1", "sort_order": 5},
    {"name": "Chocolates & Sweets", "slug": "chocolates-sweets", "emoji": "\U0001F36B", "sort_order": 6},
    {"name": "Flowers & Plants", "slug": "flowers-plants", "emoji": "\U0001F490", "sort_order": 7},
]


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
    finally:
        db.close()


if __name__ == "__main__":
    main()
