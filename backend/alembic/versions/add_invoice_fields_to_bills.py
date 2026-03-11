"""Add invoice fields to bills table

Revision ID: add_invoice_fields_to_bills
Revises: add_meeting_transcript_columns
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_invoice_fields_to_bills'
down_revision = 'add_meeting_transcript_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make shop_id nullable (invoices can exist without a shop/lead)
    op.alter_column('bills', 'shop_id', existing_type=sa.Integer(), nullable=True)

    # Client snapshot columns
    op.add_column('bills', sa.Column('invoice_client_name', sa.String(), nullable=True))
    op.add_column('bills', sa.Column('invoice_client_phone', sa.String(), nullable=True))
    op.add_column('bills', sa.Column('invoice_client_email', sa.String(), nullable=True))
    op.add_column('bills', sa.Column('invoice_client_address', sa.Text(), nullable=True))
    op.add_column('bills', sa.Column('invoice_client_org', sa.String(), nullable=True))

    # Invoice lifecycle status (separate from legacy 'status')
    op.add_column('bills', sa.Column('invoice_status', sa.String(), server_default='DRAFT', nullable=True))

    # Service description
    op.add_column('bills', sa.Column('service_description', sa.Text(), nullable=True))

    # Audit
    op.add_column('bills', sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('bills', sa.Column('verified_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
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
    op.drop_column('bills', 'verified_at')
    op.drop_column('bills', 'verified_by_id')
    op.drop_column('bills', 'created_by_id')
    op.drop_column('bills', 'service_description')
    op.drop_column('bills', 'invoice_status')
    op.drop_column('bills', 'invoice_client_org')
    op.drop_column('bills', 'invoice_client_address')
    op.drop_column('bills', 'invoice_client_email')
    op.drop_column('bills', 'invoice_client_phone')
    op.drop_column('bills', 'invoice_client_name')
    op.alter_column('bills', 'shop_id', existing_type=sa.Integer(), nullable=False)
