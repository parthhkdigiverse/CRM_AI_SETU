"""merge heads

Revision ID: a8285865e14f
Revises: unified_status_pipeline, a711487ea316
Create Date: 2026-03-17 17:01:51.461213

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8285865e14f'
down_revision: Union[str, Sequence[str], None] = ('unified_status_pipeline', 'a711487ea316')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
