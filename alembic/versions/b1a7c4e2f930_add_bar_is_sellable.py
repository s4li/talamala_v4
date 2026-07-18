"""add is_sellable to bars

Sellability gate for bars. Site inventory count and every sales channel
(shop, cart, checkout, dealer POS, customer POS, dealer API, Rasis) count
only bars with is_sellable = true. Opt-in: defaults to false.

Revision ID: b1a7c4e2f930
Revises: 0cb882b1a8db
Create Date: 2026-07-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b1a7c4e2f930'
down_revision: Union[str, None] = '0cb882b1a8db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'bars',
        sa.Column('is_sellable', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index('ix_bars_is_sellable', 'bars', ['is_sellable'])


def downgrade() -> None:
    op.drop_index('ix_bars_is_sellable', table_name='bars')
    op.drop_column('bars', 'is_sellable')
