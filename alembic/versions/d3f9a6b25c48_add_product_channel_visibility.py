"""add per-channel visibility flags to products

is_hidden_in_shop / is_hidden_in_pos let a product be pulled from one sales
channel without deactivating it everywhere. Opt-in: both default to false, so
existing products keep their current visibility.

Revision ID: d3f9a6b25c48
Revises: c2d8e5f14a37
Create Date: 2026-07-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd3f9a6b25c48'
down_revision: Union[str, None] = 'c2d8e5f14a37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'products',
        sa.Column('is_hidden_in_shop', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'products',
        sa.Column('is_hidden_in_pos', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index('ix_products_is_hidden_in_shop', 'products', ['is_hidden_in_shop'])
    op.create_index('ix_products_is_hidden_in_pos', 'products', ['is_hidden_in_pos'])


def downgrade() -> None:
    op.drop_index('ix_products_is_hidden_in_pos', table_name='products')
    op.drop_index('ix_products_is_hidden_in_shop', table_name='products')
    op.drop_column('products', 'is_hidden_in_pos')
    op.drop_column('products', 'is_hidden_in_shop')
