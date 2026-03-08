"""merge_heads_fix_scheduler

Revision ID: 7dc756e93ac9
Revises: 87c6b6f81a60, bcddca20c680
Create Date: 2026-03-08 14:54:33.046344

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7dc756e93ac9'
down_revision: Union[str, Sequence[str], None] = ('87c6b6f81a60', 'bcddca20c680')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
