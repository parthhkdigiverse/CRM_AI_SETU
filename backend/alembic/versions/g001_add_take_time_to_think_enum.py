# backend/alembic/versions/g001_add_take_time_to_think_enum.py
"""Add TAKE_TIME_TO_THINK to visitstatus enum

Revision ID: g001_add_take_time_to_think_enum
Revises: f001_merge_heads
Create Date: 2026-03-11 23:51:00.000000

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'g001_add_take_time_to_think_enum'
down_revision: Union[str, tuple, None] = ('f001_merge_heads', '7b5c53727dee')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE cannot run inside a transaction block in PostgreSQL
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE visitstatus ADD VALUE IF NOT EXISTS 'TAKE_TIME_TO_THINK';")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values — no-op
    pass
