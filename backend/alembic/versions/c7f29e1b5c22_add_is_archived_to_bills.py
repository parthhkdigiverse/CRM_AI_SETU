"""add is_archived to bills

Revision ID: c7f29e1b5c22
Revises: d2f1b6a9c3e4
Create Date: 2026-03-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7f29e1b5c22"
down_revision: Union[str, Sequence[str], None] = "d2f1b6a9c3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bills", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("bills", "is_archived", server_default=None)


def downgrade() -> None:
    op.drop_column("bills", "is_archived")
