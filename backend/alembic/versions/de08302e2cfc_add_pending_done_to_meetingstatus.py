# backend/alembic/versions/de08302e2cfc_add_pending_done_to_meetingstatus.py
"""add_pending_done_to_meetingstatus

Revision ID: de08302e2cfc
Revises: d148191278bc
Create Date: 2026-03-06 10:46:42.970317

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'de08302e2cfc'
down_revision: Union[str, Sequence[str], None] = 'd148191278bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- Enum value additions must run OUTSIDE a transaction in PostgreSQL ---
    # Commit any open transaction first, then add the new enum values.
    connection = op.get_bind()
    connection.execute(sa.text("COMMIT"))
    connection.execute(sa.text("ALTER TYPE meetingstatus ADD VALUE IF NOT EXISTS 'PENDING'"))
    connection.execute(sa.text("ALTER TYPE meetingstatus ADD VALUE IF NOT EXISTS 'DONE'"))

    # --- Auto-generated column changes (inside a new implicit transaction) ---
    # Cast TEXT -> JSON requires explicit USING clause for PostgreSQL
    op.execute(
        "ALTER TABLE meeting_summaries ALTER COLUMN ai_summary TYPE JSON "
        "USING ai_summary::json"
    )
    op.alter_column('meeting_summaries', 'reminder_sent',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('false'))
    op.create_index(
        op.f('ix_meeting_summaries_calendar_event_id'),
        'meeting_summaries', ['calendar_event_id'], unique=False,
        if_not_exists=True
    )
    op.alter_column('notifications', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL does not support removing enum values.
    # Only the column-level changes are reverted here.
    op.alter_column('notifications', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.drop_index(op.f('ix_meeting_summaries_calendar_event_id'), table_name='meeting_summaries')
    op.alter_column('meeting_summaries', 'reminder_sent',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('false'))
    op.execute(
        "ALTER TABLE meeting_summaries ALTER COLUMN ai_summary TYPE TEXT "
        "USING ai_summary::text"
    )
