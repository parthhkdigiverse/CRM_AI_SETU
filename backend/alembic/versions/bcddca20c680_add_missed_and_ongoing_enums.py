"""add_missed_and_ongoing_enums

Revision ID: bcddca20c680
Revises: a1d03e23043f
Create Date: 2026-03-08 13:58:54.543341

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bcddca20c680'
down_revision: Union[str, Sequence[str], None] = 'a1d03e23043f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Add new Enum values to PostgreSQL types."""
    # ProjectStatus: add ONGOING
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'ONGOING'")
    
    # IssueStatus: add OPEN and IN_PROGRESS
    op.execute("ALTER TYPE issuestatus ADD VALUE IF NOT EXISTS 'OPEN'")
    op.execute("ALTER TYPE issuestatus ADD VALUE IF NOT EXISTS 'IN_PROGRESS'")
    
    # VisitStatus: add new tracking labels
    op.execute("ALTER TYPE visitstatus ADD VALUE IF NOT EXISTS 'MISSED'")
    op.execute("ALTER TYPE visitstatus ADD VALUE IF NOT EXISTS 'COMPLETED'")
    op.execute("ALTER TYPE visitstatus ADD VALUE IF NOT EXISTS 'CANCELLED'")
    op.execute("ALTER TYPE visitstatus ADD VALUE IF NOT EXISTS 'SCHEDULED'")

def downgrade() -> None:
    """
    Note: PostgreSQL does not support easy removal of Enum values. 
    Downgrade typically requires dropping and recreating the type, 
    which can lead to data loss if not handled with care.
    """
    pass