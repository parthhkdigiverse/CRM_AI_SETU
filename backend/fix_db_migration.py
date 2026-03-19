import psycopg2
from urllib.parse import urlparse, unquote
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())
try:
    from app.core.config import settings
except ImportError:
    class Settings: DATABASE_URL = "postgresql://postgres:0412@localhost:5432/AI%20SETU"
    settings = Settings()

def get_conn():
    parsed = urlparse(settings.DATABASE_URL)
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=unquote(parsed.path.lstrip("/")),
        user=parsed.username,
        password=unquote(parsed.password) if parsed.password else "",
    )

def fix_schema():
    conn = get_conn()
    cur = conn.cursor()
    try:
        # 1. Shops table additions
        print("Checking shops table...")
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'shops'")
        shops_cols = [r[0] for r in cur.fetchall()]
        
        shop_additions = [
            ("project_type", "VARCHAR"),
            ("requirements", "TEXT"),
            ("pipeline_stage", "VARCHAR DEFAULT 'LEAD'"),
            ("assignment_status", "VARCHAR DEFAULT 'UNASSIGNED'"),
            ("assigned_by_id", "INTEGER"),
            ("accepted_at", "TIMESTAMP"),
            ("created_by_id", "INTEGER"),
            ("project_manager_id", "INTEGER"),
            ("demo_stage", "INTEGER DEFAULT 0"),
            ("demo_scheduled_at", "TIMESTAMP"),
            ("demo_title", "VARCHAR"),
            ("demo_type", "VARCHAR"),
            ("demo_notes", "TEXT"),
            ("demo_meet_link", "VARCHAR")
        ]
        
        for col, dtype in shop_additions:
            if col not in shops_cols:
                print(f"Adding column {col} to shops...")
                cur.execute(f"ALTER TABLE shops ADD COLUMN {col} {dtype}")

        # 2. Visits table additions
        print("Checking visits table...")
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'visits'")
        visits_cols = [r[0] for r in cur.fetchall()]
        
        visit_additions = [
            ("decline_remarks", "TEXT")
        ]
        
        for col, dtype in visit_additions:
            if col not in visits_cols:
                print(f"Adding column {col} to visits...")
                cur.execute(f"ALTER TABLE visits ADD COLUMN {col} {dtype}")

        conn.commit()
        print("Schema sync complete!")
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    fix_schema()
