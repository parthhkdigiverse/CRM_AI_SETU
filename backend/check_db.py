from sqlalchemy import create_engine

# Use the exact same URL as in alembic.ini
DATABASE_URL = "postgresql://postgres:Nency%40307@localhost:5432/crm_ai_setu"

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Success! Database connection is working.")
except Exception as e:
    print(f"Error: {e}")
    