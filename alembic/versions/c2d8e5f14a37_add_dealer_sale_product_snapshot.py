"""add product snapshot columns to dealer_sales

DealerSale.bar_id and Bar.product_id are both ON DELETE SET NULL, so deleting a
bar or a product silently erased the product name/weight from the dealer sales
report — and dropped those rows out of the weight/wage aggregates entirely,
because the report joined Product through Bar.

Snapshot the product facts on the sale row at sale time so the report stays
correct forever. Existing rows are backfilled from the live join where it is
still intact.

Revision ID: c2d8e5f14a37
Revises: b1a7c4e2f930
Create Date: 2026-07-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c2d8e5f14a37'
down_revision: Union[str, None] = 'b1a7c4e2f930'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('dealer_sales', sa.Column('product_id', sa.Integer(), nullable=True))
    op.add_column('dealer_sales', sa.Column('product_name', sa.String(), nullable=True))
    op.add_column('dealer_sales', sa.Column('product_weight', sa.Numeric(10, 3), nullable=True))
    op.add_column('dealer_sales', sa.Column('product_purity', sa.Numeric(6, 1), nullable=True))
    op.add_column('dealer_sales', sa.Column('applied_wage_percent', sa.Numeric(5, 2), nullable=True))
    op.add_column('dealer_sales', sa.Column('serial_code', sa.String(), nullable=True))

    op.create_foreign_key(
        'fk_dealer_sales_product_id', 'dealer_sales', 'products',
        ['product_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index('ix_dealer_sales_product_id', 'dealer_sales', ['product_id'])
    op.create_index('ix_dealer_sales_serial_code', 'dealer_sales', ['serial_code'])

    # Backfill from the live join while it still exists.
    op.execute("""
        UPDATE dealer_sales ds
        SET product_id           = p.id,
            product_name         = p.name,
            product_weight       = p.weight,
            product_purity       = p.purity,
            applied_wage_percent = p.wage,
            serial_code          = b.serial_code
        FROM bars b
        JOIN products p ON p.id = b.product_id
        WHERE ds.bar_id = b.id
          AND ds.product_id IS NULL
    """)

    # Sales whose bar survives but whose product is already gone: keep the serial.
    op.execute("""
        UPDATE dealer_sales ds
        SET serial_code = b.serial_code
        FROM bars b
        WHERE ds.bar_id = b.id
          AND ds.serial_code IS NULL
    """)


def downgrade() -> None:
    op.drop_index('ix_dealer_sales_serial_code', table_name='dealer_sales')
    op.drop_index('ix_dealer_sales_product_id', table_name='dealer_sales')
    op.drop_constraint('fk_dealer_sales_product_id', 'dealer_sales', type_='foreignkey')
    op.drop_column('dealer_sales', 'serial_code')
    op.drop_column('dealer_sales', 'applied_wage_percent')
    op.drop_column('dealer_sales', 'product_purity')
    op.drop_column('dealer_sales', 'product_weight')
    op.drop_column('dealer_sales', 'product_name')
    op.drop_column('dealer_sales', 'product_id')
