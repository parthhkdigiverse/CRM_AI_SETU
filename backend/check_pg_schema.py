import psycopg2
from urllib.parse import urlparse, unquote
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())
from app.core.config import settings

def get_conn():
    parsed = urlparse(settings.DATABASE_URL)
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=unquote(parsed.path.lstrip("/")),
        user=parsed.username,
        password=unquote(parsed.password) if parsed.password else "",
    )

def check_columns(table_name):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
        cols = [r[0] for r in cur.fetchall()]
        print(f"Columns in {table_name}: {cols}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    check_columns("shops")
    check_columns("visits")
