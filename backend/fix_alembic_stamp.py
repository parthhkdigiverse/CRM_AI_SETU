# backend/fix_alembic_stamp.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from alembic.config import Config
from alembic import command

alembic_cfg = Config("alembic.ini")
try:
    command.upgrade(alembic_cfg, "head")
    print("Migration succeeded!")
except Exception as e:
    print(f"Migration failed: {e}")
    import traceback
    traceback.print_exc()
