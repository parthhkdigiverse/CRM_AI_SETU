"""add missing statuses to visitstatus enum

Revision ID: 6b99aedf62e5
Revises: h003_merge_heads
Create Date: 2026-03-13 09:28:18.446310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b99aedf62e5'
down_revision: Union[str, Sequence[str], None] = 'h003_merge_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # PostgreSQL requires ALTER TYPE ... ADD VALUE to run outside a transaction block
    op.execute("COMMIT")
    op.execute("ALTER TYPE visitstatus ADD VALUE IF NOT EXISTS 'SATISFIED'")
    op.execute("ALTER TYPE visitstatus ADD VALUE IF NOT EXISTS 'ACCEPT'")
    op.execute("ALTER TYPE visitstatus ADD VALUE IF NOT EXISTS 'DECLINE'")
    op.execute("ALTER TYPE visitstatus ADD VALUE IF NOT EXISTS 'OTHER'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
