"""Add get_category_ids() Postgres function

The Category ORM model's get_descendant_ids() helper (used by product
category filtering, including subcategories) calls this Postgres function,
but it was never captured in a migration - it apparently only ever existed
in an earlier dev database, so every fresh database (including Girnar's)
is missing it, causing a 500 on any product-list request filtered by a
category slug (e.g. GET /api/product/all?category=Bags+%26+Pouches).

Returns the given category's own id plus every descendant id (children,
grandchildren, ...) in one recursive query, so filtering by a parent
category correctly includes its sub-categories' products too.

Revision ID: a4f2c8e91d3b
Revises: 97fc59b3d306
Create Date: 2026-07-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a4f2c8e91d3b'
down_revision: Union[str, None] = '97fc59b3d306'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION get_category_ids(input_slug TEXT)
        RETURNS TABLE(category_id UUID) AS $$
        BEGIN
            RETURN QUERY
            WITH RECURSIVE category_tree AS (
                SELECT id FROM categories WHERE slug = input_slug
                UNION ALL
                SELECT c.id
                FROM categories c
                INNER JOIN category_tree ct ON c.parent_id = ct.id
            )
            SELECT id FROM category_tree;
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS get_category_ids(TEXT);")
