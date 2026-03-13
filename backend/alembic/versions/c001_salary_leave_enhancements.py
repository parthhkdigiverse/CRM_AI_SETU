"""salary_and_leave_enhancements

Revision ID: c001_salary_leave
Revises: 87c6b6f81a60, bcddca20c680
Create Date: 2026-03-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c001_salary_leave'
down_revision: Union[str, Sequence[str], None] = ('87c6b6f81a60', 'bcddca20c680')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Leave Records: add leave_type column
    op.add_column(
        'leave_records',
        sa.Column('leave_type', sa.String(), nullable=False, server_default='CASUAL')
    )

    # Leave Records: add day_type column (FULL / HALF)
    op.add_column(
        'leave_records',
        sa.Column('day_type', sa.String(), nullable=False, server_default='FULL')
    )

    # Salary Slips: add incentive_amount column
    op.add_column(
        'salary_slips',
        sa.Column('incentive_amount', sa.Float(), nullable=False, server_default='0')
    )

    # Salary Slips: add total_earnings column
    op.add_column(
        'salary_slips',
        sa.Column('total_earnings', sa.Float(), nullable=False, server_default='0')
    )

    # Salary Slips: add slab_bonus column
    op.add_column(
        'salary_slips',
        sa.Column('slab_bonus', sa.Float(), nullable=False, server_default='0')
    )

    # Salary Slips: add status column (DRAFT / CONFIRMED)
    op.add_column(
        'salary_slips',
        sa.Column('status', sa.String(), nullable=False, server_default='CONFIRMED')
    )

    # Salary Slips: add confirmed_by column
    op.add_column(
        'salary_slips',
        sa.Column('confirmed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True)
    )

    # Salary Slips: add confirmed_at column
    op.add_column(
        'salary_slips',
        sa.Column('confirmed_at', sa.Date(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('salary_slips', 'confirmed_at')
    op.drop_column('salary_slips', 'confirmed_by')
    op.drop_column('salary_slips', 'status')
    op.drop_column('salary_slips', 'slab_bonus')
    op.drop_column('salary_slips', 'total_earnings')
    op.drop_column('salary_slips', 'incentive_amount')
    op.drop_column('leave_records', 'day_type')
    op.drop_column('leave_records', 'leave_type')
