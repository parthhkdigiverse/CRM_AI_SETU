"""merge master branch updates

Revision ID: 30e8b3254fef
Revises: 6b99aedf62e5, d2f1b6a9c3e4
Create Date: 2026-03-13 10:40:38.492260

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30e8b3254fef'
down_revision: Union[str, Sequence[str], None] = ('6b99aedf62e5', 'd2f1b6a9c3e4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
