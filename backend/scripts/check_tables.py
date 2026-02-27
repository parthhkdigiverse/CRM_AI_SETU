import sys
import os

# Define paths
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")

# Ensure paths are in sys.path correctly
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
tables = inspector.get_table_names()
print("Tables found in database:")
for table in tables:
    print(f"- {table}")

required_tables = ["users", "activity_logs"]
failed = False
for req in required_tables:
    if req not in tables:
        print(f"CRITICAL: Table '{req}' is MISSING!")
        failed = True
    else:
        print(f"Table '{req}' is present.")

if failed:
    sys.exit(1)
