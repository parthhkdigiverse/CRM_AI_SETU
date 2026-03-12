"""Add slab_bonus_amount to incentive_slips

Revision ID: d1a9f3b72e84
Revises: add_invoice_fields_to_bills
Create Date: 2026-03-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'd1a9f3b72e84'
down_revision: Union[str, Sequence[str], None] = ('add_invoice_fields_to_bills', 'c003_add_billing_invoice_columns')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {c["name"] for c in inspector.get_columns("incentive_slips")}
    if 'slab_bonus_amount' not in existing_columns:
        op.add_column(
            'incentive_slips',
            sa.Column('slab_bonus_amount', sa.Float(), nullable=True, server_default='0')
        )


def downgrade() -> None:
    op.drop_column('incentive_slips', 'slab_bonus_amount')
