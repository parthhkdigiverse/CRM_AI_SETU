"""Convert incentive_slips.applied_slab to string

Revision ID: d2f1b6a9c3e4
Revises: c7f5b1a4e210
Create Date: 2026-03-12 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'd2f1b6a9c3e4'
down_revision: Union[str, Sequence[str], None] = 'c7f5b1a4e210'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c['name']: c for c in inspector.get_columns('incentive_slips')}
    if 'applied_slab' not in columns:
        return

    current_type = columns['applied_slab']['type']
    dialect = bind.dialect.name

    if not isinstance(current_type, sa.String):
        if dialect == 'postgresql':
            op.execute(
                """
                ALTER TABLE incentive_slips
                ALTER COLUMN applied_slab TYPE VARCHAR(32)
                USING (
                    CASE
                        WHEN applied_slab IS NULL THEN NULL
                        WHEN applied_slab::text IN ('0', '0.0') THEN NULL
                        ELSE applied_slab::text
                    END
                )
                """
            )
        else:
            with op.batch_alter_table('incentive_slips') as batch_op:
                batch_op.alter_column(
                    'applied_slab',
                    existing_type=current_type,
                    type_=sa.String(length=32),
                    existing_nullable=True,
                )

    op.execute("UPDATE incentive_slips SET applied_slab = NULL WHERE applied_slab IN ('0', '0.0', '')")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c['name']: c for c in inspector.get_columns('incentive_slips')}
    if 'applied_slab' not in columns:
        return

    current_type = columns['applied_slab']['type']
    dialect = bind.dialect.name

    if isinstance(current_type, sa.String):
        # Preserve non-numeric slab labels by nulling them before float conversion.
        if dialect == 'postgresql':
            op.execute(
                """
                UPDATE incentive_slips
                SET applied_slab = NULL
                WHERE applied_slab IS NOT NULL
                  AND applied_slab !~ '^[0-9]+(\\.[0-9]+)?$'
                """
            )
            op.execute(
                """
                ALTER TABLE incentive_slips
                ALTER COLUMN applied_slab TYPE DOUBLE PRECISION
                USING applied_slab::double precision
                """
            )
        else:
            op.execute(
                """
                UPDATE incentive_slips
                SET applied_slab = NULL
                WHERE applied_slab IS NOT NULL
                  AND applied_slab NOT GLOB '[0-9]*'
                """
            )
            with op.batch_alter_table('incentive_slips') as batch_op:
                batch_op.alter_column(
                    'applied_slab',
                    existing_type=current_type,
                    type_=sa.Float(),
                    existing_nullable=True,
                )
