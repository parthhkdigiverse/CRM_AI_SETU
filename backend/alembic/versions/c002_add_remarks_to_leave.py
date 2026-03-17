# backend/alembic/versions/c002_add_remarks_to_leave.py
"""add_remarks_to_leave_records

Revision ID: c002_add_remarks_to_leave
Revises: c001_salary_leave
Create Date: 2026-03-10 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c002_add_remarks_to_leave'
down_revision: Union[str, Sequence[str], None] = 'c001_salary_leave'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('leave_records', sa.Column('remarks', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('leave_records', 'remarks')
