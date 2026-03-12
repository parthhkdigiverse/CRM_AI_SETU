"""Add incentive_enabled to users

Revision ID: c7f5b1a4e210
Revises: d1a9f3b72e84
Create Date: 2026-03-12 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'c7f5b1a4e210'
down_revision: Union[str, Sequence[str], None] = 'g001_add_take_time_to_think_enum'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {c["name"] for c in inspector.get_columns("users")}
    if 'incentive_enabled' not in existing_columns:
        op.add_column(
            'users',
            sa.Column('incentive_enabled', sa.Boolean(), nullable=False, server_default=sa.true())
        )


def downgrade() -> None:
    op.drop_column('users', 'incentive_enabled')
