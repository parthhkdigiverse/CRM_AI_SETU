import sys
from sqlalchemy import create_engine, text
from app.core.config import settings

from sqlalchemy import create_engine, text, inspect

def test_connection():
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("Connection successful!")
            
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"Tables found: {', '.join(tables)}")
            
            expected_tables = {'users', 'clients', 'projects', 'issues', 'meeting_summaries', 'alembic_version'}
            found_expected = expected_tables.intersection(set(tables))
            if found_expected:
                print(f"Verified tables: {', '.join(found_expected)}")
            else:
                print("No expected tables found.")
                
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_connection()
