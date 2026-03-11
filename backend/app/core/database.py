from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import make_url
from app.core.config import settings

# Use make_url to properly handle encoded characters (like %20 for spaces)
url = make_url(settings.DATABASE_URL)
engine = create_engine(url)
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
