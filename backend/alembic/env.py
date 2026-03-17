# backend/alembic/env.py
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.models.base import Base
# ------------------------------------------

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    # --- 2. UPDATE OFFLINE MODE TO USE SETTINGS ---
    url = str(settings.DATABASE_URL) 
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    
    # --- 3. FORCE STRING CONVERSION ---
    # Sometimes Pydantic DSN objects need to be explicitly cast to string
    configuration["sqlalchemy.url"] = str(settings.DATABASE_URL)
    
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    from urllib.parse import urlparse, unquote
    import psycopg2

    parsed = urlparse(settings.DATABASE_URL)
    connectable = engine_from_config(
        {"sqlalchemy.url": "postgresql+psycopg2://"},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        creator=lambda: psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            dbname=unquote(parsed.path.lstrip("/")),
            user=parsed.username,
            password=unquote(parsed.password) if parsed.password else "",
        ),
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

# ... rest of file ...
# --- ADD THIS AT THE VERY BOTTOM OF YOUR env.py ---

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()