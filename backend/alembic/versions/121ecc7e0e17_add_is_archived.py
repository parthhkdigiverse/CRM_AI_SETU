# backend/alembic/versions/121ecc7e0e17_add_is_archived.py
"""add_is_archived

Revision ID: 121ecc7e0e17
Revises: b51eb201accd
Create Date: 2026-03-10 11:47:42.604099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '121ecc7e0e17'
down_revision: Union[str, Sequence[str], None] = 'b51eb201accd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('areas', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('shops', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('shops', 'is_archived')
    op.drop_column('areas', 'is_archived')
