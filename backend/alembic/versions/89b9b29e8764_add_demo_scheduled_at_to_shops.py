"""add demo_scheduled_at to shops

Revision ID: 89b9b29e8764
Revises: 30e8b3254fef
Create Date: 2026-03-13 11:17:06.955419

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89b9b29e8764'
down_revision: Union[str, Sequence[str], None] = '30e8b3254fef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('shops', sa.Column('demo_scheduled_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('shops', 'demo_scheduled_at')
