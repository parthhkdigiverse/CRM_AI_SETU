"""resolve_schema_conflict

Revision ID: fa81632df7be
Revises: c002_add_remarks_to_leave
Create Date: 2026-03-11 13:27:50.263230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa81632df7be'
down_revision: Union[str, Sequence[str], None] = 'c002_add_remarks_to_leave'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
