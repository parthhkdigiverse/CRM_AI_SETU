"""merge_issue_statuses_and_conflicts

Revision ID: 7b5c53727dee
Revises: a001_update_issue_statuses, a979df1b8bee, c002_add_remarks_to_leave
Create Date: 2026-03-11 14:57:01.227128

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b5c53727dee'
down_revision: Union[str, Sequence[str], None] = ('a001_update_issue_statuses', 'a979df1b8bee', 'c002_add_remarks_to_leave')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
