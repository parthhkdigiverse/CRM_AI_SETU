# backend/query_alembic.py
import sys
sys.path.insert(0, 'e:/CRM AI SETU/backend')
from sqlalchemy import text
from app.core.database import engine
with engine.connect() as c:
    rows = c.execute(text('SELECT version_num FROM alembic_version'))
    print([r[0] for r in rows])
