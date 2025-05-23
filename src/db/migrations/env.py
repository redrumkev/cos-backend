# src/db/migrations/env.py

"""Alembic environment setup for COS migrations."""

# --- Standard library imports ---
import os
import sys
from logging.config import fileConfig
from pathlib import Path

# --- Patch sys.path for robust module resolution ---
PROJECT_ROOT = (Path(__file__).parent.parent.parent).resolve()
SRC_DIR = (PROJECT_ROOT / "src").resolve()
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- Third-party imports ---
try:
    from dotenv import load_dotenv

    DOTENV_PATH = (PROJECT_ROOT / ".env").resolve()
    load_dotenv(str(DOTENV_PATH), override=False)
except ImportError:
    pass

from alembic import context
from sqlalchemy import engine_from_config, pool

# --- Local application imports (after sys.path patch) ---
from src.backend.cc import models as cc_models  # noqa: F401
from src.db.base import Base

# --- Alembic config and logging ---
config = context.config
fileConfig(config.config_file_name)

# --- Database URL logic (sync for migrations) ---
migrate_url = os.getenv("POSTGRES_MIGRATE_URL")
if not migrate_url:
    dev_url = os.getenv("POSTGRES_DEV_URL")
    if dev_url and "+asyncpg" in dev_url:
        migrate_url = dev_url.replace("+asyncpg", "+psycopg")
    else:
        migrate_url = dev_url
if not migrate_url:
    raise RuntimeError("No database URL found for Alembic migrations.")
config.set_main_option("sqlalchemy.url", migrate_url)

# --- Target metadata for autogenerate ---
target_metadata = Base.metadata


# --- Migration routines ---
def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

# ruff: noqa: E402
