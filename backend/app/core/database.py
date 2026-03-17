# backend/app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import urlparse, unquote
import psycopg2
from app.core.config import settings

# Parse the DATABASE_URL manually so URL-encoded characters (e.g. %20 for space)
# are properly decoded before being passed to psycopg2.
def _make_psycopg2_connection():
    parsed = urlparse(settings.DATABASE_URL)
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=unquote(parsed.path.lstrip("/")),
        user=parsed.username,
        password=unquote(parsed.password) if parsed.password else "",
    )

engine = create_engine("postgresql+psycopg2://", creator=_make_psycopg2_connection)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    from sqlalchemy import inspect, text
    Base.metadata.create_all(bind=engine)
    
    # Manual schema checks for existing tables
    inspector = inspect(engine)
    with engine.connect() as conn:
        # 1. incentive_slabs
        if inspector.has_table("incentive_slabs"):
            cols = [c['name'] for c in inspector.get_columns('incentive_slabs')]
            if 'min_units' not in cols:
                conn.execute(text("ALTER TABLE incentive_slabs ADD COLUMN min_units INTEGER DEFAULT 1"))
            if 'max_units' not in cols:
                conn.execute(text("ALTER TABLE incentive_slabs ADD COLUMN max_units INTEGER DEFAULT 10"))
            if 'incentive_per_unit' not in cols:
                conn.execute(text("ALTER TABLE incentive_slabs ADD COLUMN incentive_per_unit FLOAT DEFAULT 0.0"))
            if 'slab_bonus' not in cols:
                conn.execute(text("ALTER TABLE incentive_slabs ADD COLUMN slab_bonus FLOAT DEFAULT 0.0"))
        
        # 2. incentive_slips
        if inspector.has_table("incentive_slips"):
            cols = [c['name'] for c in inspector.get_columns('incentive_slips')]
            if 'amount_per_unit' not in cols:
                conn.execute(text("ALTER TABLE incentive_slips ADD COLUMN amount_per_unit FLOAT DEFAULT 0.0"))

        # 3. bills (invoice workflow extensions)
        if inspector.has_table("bills"):
            cols = [c['name'] for c in inspector.get_columns('bills')]
            if 'payment_type' not in cols:
                conn.execute(text("ALTER TABLE bills ADD COLUMN payment_type VARCHAR DEFAULT 'PERSONAL_ACCOUNT'"))
            if 'gst_type' not in cols:
                conn.execute(text("ALTER TABLE bills ADD COLUMN gst_type VARCHAR DEFAULT 'WITH_GST'"))
            if 'invoice_series' not in cols:
                conn.execute(text("ALTER TABLE bills ADD COLUMN invoice_series VARCHAR DEFAULT 'INV'"))
            if 'invoice_sequence' not in cols:
                conn.execute(text("ALTER TABLE bills ADD COLUMN invoice_sequence INTEGER DEFAULT 1"))
            if 'requires_qr' not in cols:
                conn.execute(text("ALTER TABLE bills ADD COLUMN requires_qr BOOLEAN DEFAULT TRUE"))
        
        # 4. Global Deletion Policy & Soft Delete Column Checks
        tables_to_check = [
            "clients", "projects", "issues", "areas", "shops", "todos", 
            "meeting_summaries", "bills", "attendance", "feedbacks", 
            "user_feedbacks", "payments", "incentive_slabs", 
            "employee_performances", "incentive_slips", "notifications", 
            "timetable_events", "salary_slips", "leave_records", "visits"
        ]
        
        for table_name in tables_to_check:
            if inspector.has_table(table_name):
                cols = [c['name'] for c in inspector.get_columns(table_name)]
                if 'is_deleted' not in cols:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE"))
        
        # 5. Initialize Delete Policy if missing
        res = conn.execute(text("SELECT key FROM app_settings WHERE key = 'delete_policy'")).first()
        if not res:
            conn.execute(text("INSERT INTO app_settings (key, value) VALUES ('delete_policy', 'SOFT')"))

        
        # 3. feedbacks
        if inspector.has_table("feedbacks"):
            cols = [c['name'] for c in inspector.get_columns('feedbacks')]
            if 'mobile' not in cols:
                conn.execute(text("ALTER TABLE feedbacks ADD COLUMN mobile VARCHAR"))
            if 'shop_name' not in cols:
                conn.execute(text("ALTER TABLE feedbacks ADD COLUMN shop_name VARCHAR"))
            if 'product' not in cols:
                conn.execute(text("ALTER TABLE feedbacks ADD COLUMN product VARCHAR"))
            if 'agent_name' not in cols:
                conn.execute(text("ALTER TABLE feedbacks ADD COLUMN agent_name VARCHAR"))
            if 'referral_code' not in cols:
                conn.execute(text("ALTER TABLE feedbacks ADD COLUMN referral_code VARCHAR"))
        
        # 4. users
        if inspector.has_table("users"):
            cols = [c['name'] for c in inspector.get_columns('users')]
            if 'referral_code' not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN referral_code VARCHAR"))
        
        conn.commit()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
