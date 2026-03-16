"""fix multiple heads

Revision ID: 0e7917045276
Revises: c7f5b1a4e210, d1a9f3b72e84
Create Date: 2026-03-12 16:29:08.619663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e7917045276'
down_revision: Union[str, Sequence[str], None] = ('c7f5b1a4e210', 'd1a9f3b72e84')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
