"""Add is_custom_bundle / bundle_items columns to products

Backs the "build your own hamper" feature: a hamper is materialized as
a real Product row (so it flows through the existing cart/order
pipeline unchanged) but flagged so storefront listings can hide it.

Revision ID: b7c1d4e29f6a
Revises: a4f2c8e91d3b
Create Date: 2026-07-08 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b7c1d4e29f6a'
down_revision: Union[str, None] = 'a4f2c8e91d3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'products',
        sa.Column('is_custom_bundle', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'products',
        sa.Column('bundle_items', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('products', 'bundle_items')
    op.drop_column('products', 'is_custom_bundle')
