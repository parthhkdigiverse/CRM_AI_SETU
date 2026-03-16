# backend/alembic/versions/b2fb7edd1387_add_archived_by.py
"""add_archived_by

Revision ID: b2fb7edd1387
Revises: 121ecc7e0e17
Create Date: 2026-03-10 12:11:29.798783

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2fb7edd1387'
down_revision: Union[str, Sequence[str], None] = '121ecc7e0e17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('areas', sa.Column('archived_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_areas_archived_by_id', 'areas', 'users', ['archived_by_id'], ['id'])
    
    op.add_column('shops', sa.Column('archived_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_shops_archived_by_id', 'shops', 'users', ['archived_by_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_shops_archived_by_id', 'shops', type_='foreignkey')
    op.drop_column('shops', 'archived_by_id')
    
    op.drop_constraint('fk_areas_archived_by_id', 'areas', type_='foreignkey')
    op.drop_column('areas', 'archived_by_id')
