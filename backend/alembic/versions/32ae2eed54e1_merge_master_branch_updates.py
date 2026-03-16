"""merge master branch updates

Revision ID: 32ae2eed54e1
Revises: 7b8a33af3101, c7f29e1b5c22
Create Date: 2026-03-16 14:37:18.682655

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32ae2eed54e1'
down_revision: Union[str, Sequence[str], None] = ('7b8a33af3101', 'c7f29e1b5c22')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
