# src/db/migrations/env.py

"""Alembic environment setup for COS migrations."""

from __future__ import annotations

import logging
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# --- More robust sys.path patching ---
# Get the absolute path to the project root (4 levels up from this file)
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent
src_path = project_root / "src"

# Setup logging for migration environment
logger = logging.getLogger("alembic.env")

# Debug path resolution
logger.debug("Current file: %s", current_file)
logger.debug("Project root: %s", project_root)
logger.debug("Src path: %s", src_path)
logger.debug("Src exists: %s", src_path.exists())

# Add both project root and src to path
for path_to_add in [str(project_root), str(src_path)]:
    if path_to_add not in sys.path:
        sys.path.insert(0, path_to_add)
        logger.debug("Added to sys.path: %s", path_to_add)

# --- Third-party imports ---
try:
    from dotenv import load_dotenv

    # Try multiple .env locations
    env_candidates = [project_root / ".env", project_root / "infrastructure" / ".env", src_path / ".env"]

    for env_file in env_candidates:
        if env_file.exists():
            load_dotenv(str(env_file), override=False)
            logger.info("Loaded .env from: %s", env_file)
            break
    else:
        logger.warning("No .env file found in candidate locations")

except ImportError:
    logger.warning("dotenv not available, skipping .env loading")

# --- Local application imports (after sys.path patch) ---
try:
    # Import model modules to ensure metadata is registered with Base
    from src.backend.cc import mem0_models
    from src.backend.cc import models as cc_models
    from src.db.base import Base

    # Explicitly reference imports to ensure they're loaded into metadata
    _ = mem0_models, cc_models

    logger.info("Successfully imported COS modules")
except ImportError as e:
    logger.error("Import error: %s", e)
    logger.debug("Current sys.path: %s", sys.path)
    raise

# --- Alembic config and logging ---
config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# --- Database URL logic (sync for migrations) ---
migrate_url = os.getenv("POSTGRES_MIGRATE_URL")
if not migrate_url:
    # Try DATABASE_URL_TEST first (CI environment)
    test_url = os.getenv("DATABASE_URL_TEST")
    if test_url:
        migrate_url = test_url.replace("+asyncpg", "+psycopg") if "+asyncpg" in test_url else test_url
    else:
        # Fallback to dev URL
        dev_url = os.getenv("POSTGRES_DEV_URL")
        migrate_url = dev_url.replace("+asyncpg", "+psycopg") if dev_url and "+asyncpg" in dev_url else dev_url

if not migrate_url:
    raise RuntimeError(
        "No database URL found for Alembic migrations. "
        "Checked: POSTGRES_MIGRATE_URL, DATABASE_URL_TEST, POSTGRES_DEV_URL"
    )

logger.info("Using migration URL: %s", migrate_url.replace(migrate_url.split("@")[0].split("//")[1], "***"))
config.set_main_option("sqlalchemy.url", migrate_url)

# --- Target metadata for autogenerate ---
target_metadata = Base.metadata

# --- filter so Alembic only watches our schemas ------------
WATCH_SCHEMAS = {"cc", "mem0_cc"}


def include_object(obj: object, name: str, type_: str, reflected: bool, compare_to: object) -> bool:
    """Determine if an object should be included in the migration.

    Only include tables from watched schemas to avoid generating migrations
    for external/system tables.
    """
    if type_ == "table":
        # Safe type check for table objects without using assert
        if hasattr(obj, "schema"):
            return obj.schema in WATCH_SCHEMAS
        return False
    return True


# --- Migration routines ---
def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
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
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
