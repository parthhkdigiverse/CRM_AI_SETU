"""Merge two migration heads: master and nency branches

Revision ID: f001_merge_heads
Revises: ad906d96669b, e63278477e40
Create Date: 2026-03-02 11:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f001_merge_heads'
down_revision: Union[str, Sequence[str], None] = ('ad906d96669b', 'e63278477e40')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    This is a merge migration — no schema changes needed.
    Both branches already applied all required column additions to the shops table.
    
    Summary of what's already in DB from both branches:
    - source (from 181a9bd69dd3)
    - status, owner_id (from 2a03d8db8870)
    - project_type, requirements, area_id FK to areas (from ad906d96669b)
    - areas.lat, areas.lng (from e63278477e40)
    """
    pass


def downgrade() -> None:
    pass
