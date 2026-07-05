"""
Idempotent admin seed for Girnar Gifts.

Usage:
    SEED_ADMIN_EMAIL=admin@girnargifts.com SEED_ADMIN_PASSWORD='StrongPass!23' \
        python -m app.scripts.seed_admin

SEED_ADMIN_PASSWORD is required and never hardcoded. Safe to re-run: if the
admin email already exists, it does nothing.
"""
from __future__ import annotations

import os
import sys

from app.db import SessionLocal
# Import all model modules so SQLAlchemy can resolve string-based
# relationship() targets on Users (same requirement as alembic/env.py).
from app.orders import models as _orders_models  # noqa: F401
from app.cart import models as _cart_models  # noqa: F401
from app.favorite import models as _favorite_models  # noqa: F401
from app.rating import models as _rating_models  # noqa: F401
from app.products import models as _product_models  # noqa: F401
from app.users.models import Users
from app.users.utils import password_context

ADMIN_ROLE = 1


def main() -> None:
    email = os.environ.get("SEED_ADMIN_EMAIL", "admin@girnargifts.com")
    password = os.environ.get("SEED_ADMIN_PASSWORD")
    if not password:
        print("SEED_ADMIN_PASSWORD env var is required.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(Users).filter(Users.email == email).first()
        if existing:
            print(f"Admin already exists: {email} (skipping)")
            return

        admin = Users(
            email=email,
            name="Girnar Admin",
            confirmed=True,
            is_active=True,
            hashed_password=password_context.hash(password),
            role=ADMIN_ROLE,
        )
        db.add(admin)
        db.commit()
        print(f"Seeded admin: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
