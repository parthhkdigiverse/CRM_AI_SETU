# backend/alembic/versions/a001_update_issue_statuses.py
"""update_issue_statuses

Simplify IssueStatus to 4 values: PENDING, IN_PROGRESS, SOLVED, RE_OPENED.
Maps legacy statuses in existing rows:
  OPEN      -> PENDING
  RESOLVED  -> SOLVED
  COMPLETED -> SOLVED
  CANCEL    -> SOLVED
  CANCELLED -> SOLVED

Revision ID: a001_update_issue_statuses
Revises: bcddca20c680, 87c6b6f81a60
Create Date: 2026-03-11 12:00:40.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a001_update_issue_statuses'
down_revision: Union[str, Sequence[str], None] = ('bcddca20c680', '87c6b6f81a60')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remap legacy issue statuses to the new 4-value canonical set."""
    conn = op.get_bind()

    # OPEN -> PENDING
    conn.execute(
        sa.text("UPDATE issues SET status = 'PENDING' WHERE status = 'OPEN'")
    )

    # RESOLVED -> SOLVED
    conn.execute(
        sa.text("UPDATE issues SET status = 'SOLVED' WHERE status = 'RESOLVED'")
    )

    # COMPLETED -> SOLVED
    conn.execute(
        sa.text("UPDATE issues SET status = 'SOLVED' WHERE status = 'COMPLETED'")
    )

    # CANCEL -> SOLVED
    conn.execute(
        sa.text("UPDATE issues SET status = 'SOLVED' WHERE status = 'CANCEL'")
    )

    # CANCELLED -> SOLVED (in case any row has the full-word variant)
    conn.execute(
        sa.text("UPDATE issues SET status = 'SOLVED' WHERE status = 'CANCELLED'")
    )


def downgrade() -> None:
    """
    Best-effort reversal: rows mapped from OPEN go back to OPEN.
    Rows that were PENDING before the upgrade cannot be distinguished
    from converted OPEN rows, so all PENDING rows are reverted to OPEN.
    SOLVED, IN_PROGRESS, and RE_OPENED rows are left as-is.
    """
    conn = op.get_bind()

    # Revert PENDING -> OPEN (best effort)
    conn.execute(
        sa.text("UPDATE issues SET status = 'OPEN' WHERE status = 'PENDING'")
    )
