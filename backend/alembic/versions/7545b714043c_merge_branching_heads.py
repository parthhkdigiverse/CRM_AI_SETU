# backend/alembic/versions/7545b714043c_merge_branching_heads.py
"""merge branching heads

Revision ID: 7545b714043c
Revises: 55c178d5c4c3, add_meeting_transcript_columns
Create Date: 2026-03-05 12:00:14.544378

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7545b714043c'
down_revision: Union[str, Sequence[str], None] = ('55c178d5c4c3', 'add_meeting_transcript_columns')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
