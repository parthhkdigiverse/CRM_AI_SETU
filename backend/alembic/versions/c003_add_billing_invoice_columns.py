"""Add billing invoice columns (merge branch)

Revision ID: c003_add_billing_invoice_columns
Revises: fa81632df7be
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

revision = 'c003_add_billing_invoice_columns'
down_revision = 'fa81632df7be'
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def upgrade() -> None:
    if not _has_column('bills', 'invoice_client_name'):
        op.add_column('bills', sa.Column('invoice_client_name', sa.String(), nullable=True))
    if not _has_column('bills', 'invoice_client_phone'):
        op.add_column('bills', sa.Column('invoice_client_phone', sa.String(), nullable=True))
    if not _has_column('bills', 'invoice_client_email'):
        op.add_column('bills', sa.Column('invoice_client_email', sa.String(), nullable=True))
    if not _has_column('bills', 'invoice_client_address'):
        op.add_column('bills', sa.Column('invoice_client_address', sa.Text(), nullable=True))
    if not _has_column('bills', 'invoice_client_org'):
        op.add_column('bills', sa.Column('invoice_client_org', sa.String(), nullable=True))
    if not _has_column('bills', 'invoice_status'):
        op.add_column('bills', sa.Column('invoice_status', sa.String(), server_default='DRAFT', nullable=True))
    if not _has_column('bills', 'service_description'):
        op.add_column('bills', sa.Column('service_description', sa.Text(), nullable=True))
    if not _has_column('bills', 'created_by_id'):
        op.add_column('bills', sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    if not _has_column('bills', 'verified_by_id'):
        op.add_column('bills', sa.Column('verified_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    if not _has_column('bills', 'verified_at'):
        op.add_column('bills', sa.Column('verified_at', sa.DateTime(), nullable=True))

    # Backfill invoice_status from legacy status
    op.execute("""
        UPDATE bills
        SET invoice_status = CASE
            WHEN status = 'CONFIRMED' THEN 'SENT'
            WHEN status = 'CANCELLED' THEN 'DRAFT'
            ELSE 'PENDING_VERIFICATION'
        END
        WHERE invoice_status IS NULL OR invoice_status = 'DRAFT'
    """)


def downgrade() -> None:
    for col in ('verified_at', 'verified_by_id', 'created_by_id',
                'service_description', 'invoice_status', 'invoice_client_org',
                'invoice_client_address', 'invoice_client_email',
                'invoice_client_phone', 'invoice_client_name'):
        if _has_column('bills', col):
            op.drop_column('bills', col)
