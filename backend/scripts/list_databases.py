import psycopg2
import os
from dotenv import load_dotenv

env_path = os.path.join("backend", ".env")
load_dotenv(env_path)

# Try connecting to 'postgres' database to list all
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="0412",
    host="localhost",
    port="5432"
)
conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT datname FROM pg_database;")
databases = cur.fetchall()
print("Available Databases:")
for db in databases:
    print(f"- {db[0]}")
cur.close()
conn.close()
