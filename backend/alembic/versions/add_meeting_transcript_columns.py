# backend/alembic/versions/add_meeting_transcript_columns.py
"""Add calendar_event_id, transcript, ai_summary to meeting_summaries

Revision ID: add_meeting_transcript_columns
Revises: (run after latest migration)
Create Date: 2026-03-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_meeting_transcript_columns'
down_revision = ('f001_merge_heads', '528856e3f8ef')  # Merge both active heads
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add calendar_event_id column (used to link back to Google Calendar for transcript lookup)
    op.add_column(
        'meeting_summaries',
        sa.Column('calendar_event_id', sa.String(), nullable=True)
    )
    op.create_index(
        op.f('ix_meeting_summaries_calendar_event_id'),
        'meeting_summaries',
        ['calendar_event_id'],
        unique=False
    )

    # Add transcript column (raw text exported from Google Drive transcript Doc)
    op.add_column(
        'meeting_summaries',
        sa.Column('transcript', sa.Text(), nullable=True)
    )

    # Add ai_summary column (JSON: {"highlights": [...], "next_steps": "..."})
    op.add_column(
        'meeting_summaries',
        sa.Column('ai_summary', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('meeting_summaries', 'ai_summary')
    op.drop_column('meeting_summaries', 'transcript')
    op.drop_index(
        op.f('ix_meeting_summaries_calendar_event_id'),
        table_name='meeting_summaries'
    )
    op.drop_column('meeting_summaries', 'calendar_event_id')
