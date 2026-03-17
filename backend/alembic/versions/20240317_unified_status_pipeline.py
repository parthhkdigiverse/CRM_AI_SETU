"""Unified status pipeline: MasterPipelineStage + GlobalTaskStatus

Revision ID: unified_status_pipeline
Revises: (set to your current head revision)
Create Date: 2024-03-17

This migration safely converts PostgreSQL typed Enum columns to the new
two-tier status system in three phases:

  Phase 1 – Cast all affected Enum columns to VARCHAR (bypasses PG type-lock)
  Phase 2 – Remap old string values to new enum string values via UPDATE
  Phase 3 – Create new PG Enum types and cast columns to them using
             postgresql_using (done here manually since autogenerate may
             not produce the USING clause without help).

NOTE: Run `alembic revision --autogenerate -m "..."` FIRST and inspect the
      generated file. If Alembic finds the model changes, its downgrade()
      section will already exist. Replace the entire upgrade() body with
      the one below.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ── Revision identifiers ────────────────────────────────────────────────────
revision = "unified_status_pipeline"
down_revision = '32ae2eed54e1'   # <── Replace with your current Alembic head revision ID
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ════════════════════════════════════════════════════════════════════════
    # PHASE 1 – Cast every affected typed-Enum column to plain VARCHAR so
    #           PostgreSQL will accept the UPDATE statements below.
    # ════════════════════════════════════════════════════════════════════════

    # shops.status  →  shops.pipeline_stage (column rename handled separately)
    op.execute("ALTER TABLE shops ALTER COLUMN status TYPE VARCHAR USING status::VARCHAR")
    op.execute("ALTER TABLE shops RENAME COLUMN status TO pipeline_stage")

    # projects.status
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE VARCHAR USING status::VARCHAR")

    # issues.status  (was String — no cast wrapper needed, but run anyway for safety)
    op.execute("ALTER TABLE issues ALTER COLUMN status TYPE VARCHAR USING status::VARCHAR")

    # meetings.status  (was meetingstatus Enum)
    op.execute("ALTER TABLE meeting_summaries ALTER COLUMN status TYPE VARCHAR USING status::VARCHAR")

    # bills / billing table — depends on your actual table name; adjust if needed
    # op.execute("ALTER TABLE bills ALTER COLUMN status TYPE VARCHAR USING status::VARCHAR")


    # ════════════════════════════════════════════════════════════════════════
    # PHASE 2 – Remap old string values → new enum string values
    # ════════════════════════════════════════════════════════════════════════

    # --- shops.pipeline_stage (formerly status) ---
    op.execute("UPDATE shops SET pipeline_stage = 'LEAD'         WHERE pipeline_stage IN ('NEW')")
    op.execute("UPDATE shops SET pipeline_stage = 'PITCHING'     WHERE pipeline_stage IN ('CONTACTED', 'MEETING_SET')")
    op.execute("UPDATE shops SET pipeline_stage = 'NEGOTIATION'  WHERE pipeline_stage IN ('NEGOTIATION')")
    op.execute("UPDATE shops SET pipeline_stage = 'DELIVERY'     WHERE pipeline_stage IN ('CONVERTED')")
    op.execute("UPDATE shops SET pipeline_stage = 'MAINTENANCE'  WHERE pipeline_stage IN ('MAINTENANCE')")
    # Default fallback for any unrecognised values
    op.execute("""
        UPDATE shops SET pipeline_stage = 'LEAD'
        WHERE pipeline_stage NOT IN ('LEAD','PITCHING','NEGOTIATION','DELIVERY','MAINTENANCE')
    """)

    # --- projects.status ---
    op.execute("UPDATE projects SET status = 'OPEN'        WHERE status IN ('NEW','PENDING','PLANNING')")
    op.execute("UPDATE projects SET status = 'IN_PROGRESS' WHERE status IN ('ONGOING','IN_PROGRESS','CONTACTED')")
    op.execute("UPDATE projects SET status = 'BLOCKED'     WHERE status IN ('ON_HOLD','BLOCKED')")
    op.execute("UPDATE projects SET status = 'RESOLVED'    WHERE status IN ('COMPLETED','DONE','SOLVED','RESOLVED')")
    op.execute("UPDATE projects SET status = 'CANCELLED'   WHERE status IN ('CANCELLED')")
    op.execute("""
        UPDATE projects SET status = 'OPEN'
        WHERE status NOT IN ('OPEN','IN_PROGRESS','BLOCKED','RESOLVED','CANCELLED')
    """)

    # --- issues.status ---
    op.execute("UPDATE issues SET status = 'OPEN'        WHERE status IN ('NEW','PENDING','OPEN')")
    op.execute("UPDATE issues SET status = 'IN_PROGRESS' WHERE status IN ('IN_PROGRESS','ONGOING')")
    op.execute("UPDATE issues SET status = 'BLOCKED'     WHERE status IN ('ON_HOLD','BLOCKED')")
    op.execute("UPDATE issues SET status = 'RESOLVED'    WHERE status IN ('COMPLETED','DONE','SOLVED','RESOLVED')")
    op.execute("UPDATE issues SET status = 'CANCELLED'   WHERE status IN ('CANCELLED')")
    op.execute("""
        UPDATE issues SET status = 'OPEN'
        WHERE status NOT IN ('OPEN','IN_PROGRESS','BLOCKED','RESOLVED','CANCELLED')
    """)

    # --- meetings.status ---
    op.execute("UPDATE meeting_summaries SET status = 'OPEN'        WHERE status IN ('SCHEDULED','PENDING','NEW','OPEN')")
    op.execute("UPDATE meeting_summaries SET status = 'IN_PROGRESS' WHERE status IN ('IN_PROGRESS','ONGOING')")
    op.execute("UPDATE meeting_summaries SET status = 'BLOCKED'     WHERE status IN ('ON_HOLD','BLOCKED')")
    op.execute("UPDATE meeting_summaries SET status = 'RESOLVED'    WHERE status IN ('COMPLETED','DONE','RESOLVED')")
    op.execute("UPDATE meeting_summaries SET status = 'CANCELLED'   WHERE status IN ('CANCELLED')")
    op.execute("""
        UPDATE meeting_summaries SET status = 'OPEN'
        WHERE status NOT IN ('OPEN','IN_PROGRESS','BLOCKED','RESOLVED','CANCELLED')
    """)


    # ════════════════════════════════════════════════════════════════════════
    # PHASE 3 – Create the new PostgreSQL Enum types and cast the VARCHAR
    #           columns back to them using USING clause.
    # ════════════════════════════════════════════════════════════════════════

    # Create new PostgreSQL Enum types (skip if they already exist via CREATE TYPE … IF NOT EXISTS)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE masterpipelinestage AS ENUM (
                'LEAD', 'PITCHING', 'NEGOTIATION', 'DELIVERY', 'MAINTENANCE'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE globaltaskstatus AS ENUM (
                'OPEN', 'IN_PROGRESS', 'BLOCKED', 'RESOLVED', 'CANCELLED'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # Cast columns from VARCHAR → new typed Enum
    op.execute("""
        ALTER TABLE shops
        ALTER COLUMN pipeline_stage TYPE masterpipelinestage
        USING pipeline_stage::masterpipelinestage
    """)

    op.execute("""
        ALTER TABLE projects
        ALTER COLUMN status TYPE globaltaskstatus
        USING status::globaltaskstatus
    """)

    op.execute("""
        ALTER TABLE issues
        ALTER COLUMN status TYPE globaltaskstatus
        USING status::globaltaskstatus
    """)

    op.execute("""
        ALTER TABLE meeting_summaries
        ALTER COLUMN status TYPE globaltaskstatus
        USING status::globaltaskstatus
    """)

    # If bills table needs updating too, uncomment:
    # op.execute("""
    #     ALTER TABLE bills
    #     ALTER COLUMN status TYPE globaltaskstatus
    #     USING status::globaltaskstatus
    # """)


def downgrade() -> None:
    # ── Reverse Phase 3: cast back to VARCHAR ───────────────────────────────
    op.execute("ALTER TABLE shops    ALTER COLUMN pipeline_stage TYPE VARCHAR USING pipeline_stage::VARCHAR")
    op.execute("ALTER TABLE projects ALTER COLUMN status         TYPE VARCHAR USING status::VARCHAR")
    op.execute("ALTER TABLE issues   ALTER COLUMN status         TYPE VARCHAR USING status::VARCHAR")
    op.execute("ALTER TABLE meeting_summaries ALTER COLUMN status         TYPE VARCHAR USING status::VARCHAR")

    # ── Reverse Phase 2: remap new → old (best-effort) ─────────────────────
    op.execute("UPDATE shops SET pipeline_stage = 'NEW'       WHERE pipeline_stage = 'LEAD'")
    op.execute("UPDATE shops SET pipeline_stage = 'CONTACTED' WHERE pipeline_stage = 'PITCHING'")
    op.execute("UPDATE shops SET pipeline_stage = 'CONVERTED' WHERE pipeline_stage = 'DELIVERY'")

    op.execute("UPDATE projects SET status = 'PLANNING'    WHERE status = 'OPEN'")
    op.execute("UPDATE projects SET status = 'IN_PROGRESS' WHERE status = 'IN_PROGRESS'")
    op.execute("UPDATE projects SET status = 'COMPLETED'   WHERE status = 'RESOLVED'")

    op.execute("UPDATE issues SET status = 'PENDING'   WHERE status = 'OPEN'")
    op.execute("UPDATE issues SET status = 'SOLVED'    WHERE status = 'RESOLVED'")

    op.execute("UPDATE meeting_summaries SET status = 'SCHEDULED'  WHERE status = 'OPEN'")
    op.execute("UPDATE meeting_summaries SET status = 'COMPLETED'  WHERE status = 'RESOLVED'")

    # ── Reverse Phase 1: rename column back ─────────────────────────────────
    op.execute("ALTER TABLE shops RENAME COLUMN pipeline_stage TO status")

    # ── Drop the new Enum types ──────────────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS masterpipelinestage")
    op.execute("DROP TYPE IF EXISTS globaltaskstatus")
