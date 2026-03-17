"""add project_manager_id and demo_stage to shops

Revision ID: h002_add_pm_demo_stage
Revises: g001_add_take_time_to_think_enum
Create Date: 2026-03-12 20:36:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h002_add_pm_demo_stage'
down_revision = 'g001_add_take_time_to_think_enum'
branch_labels = None
depends_on = None


def upgrade():
    # Add project_manager_id FK column
    op.add_column('shops', sa.Column('project_manager_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_shops_project_manager_id_users',
        'shops', 'users',
        ['project_manager_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add demo_stage column with default 0
    op.add_column('shops', sa.Column('demo_stage', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('shops', 'demo_stage')
    op.drop_constraint('fk_shops_project_manager_id_users', 'shops', type_='foreignkey')
    op.drop_column('shops', 'project_manager_id')
