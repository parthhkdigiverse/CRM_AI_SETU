"""Add meeting fields

Revision ID: 528856e3f8ef
Revises: a975384b99f5
Create Date: 2026-03-03 17:54:13.546625

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '528856e3f8ef'
down_revision: Union[str, Sequence[str], None] = 'a975384b99f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ... (imports at the top)

def upgrade() -> None:
    # 1. Manually add this line to create the type in Postgres
    meeting_type_enum = sa.Enum('IN_PERSON', 'GOOGLE_MEET', 'VIRTUAL', name='meetingtype')
    meeting_type_enum.create(op.get_bind())

    # 2. This is the existing line that was failing
    op.add_column('meeting_summaries', sa.Column('meeting_type', meeting_type_enum, nullable=True))
    op.add_column('meeting_summaries', sa.Column('meet_link', sa.String(), nullable=True))


def downgrade() -> None:
    # 1. Drop the columns first
    op.drop_column('meeting_summaries', 'meet_link')
    op.drop_column('meeting_summaries', 'meeting_type')

    # 2. Manually add this line to remove the type from Postgres
    sa.Enum(name='meetingtype').drop(op.get_bind())
