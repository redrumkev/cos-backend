# src/db/migrations/env.py

"""Alembic environment setup for COS migrations."""

# --- Standard library imports ---
import os
import sys
from logging.config import fileConfig
from pathlib import Path

# --- More robust sys.path patching ---
# Get the absolute path to the project root (4 levels up from this file)
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent
src_path = project_root / "src"

# Debug path resolution
print(f"Current file: {current_file}")  # noqa: T201
print(f"Project root: {project_root}")  # noqa: T201
print(f"Src path: {src_path}")  # noqa: T201
print(f"Src exists: {src_path.exists()}")  # noqa: T201

# Add both project root and src to path
for path_to_add in [str(project_root), str(src_path)]:
    if path_to_add not in sys.path:
        sys.path.insert(0, path_to_add)
        print(f"Added to sys.path: {path_to_add}")  # noqa: T201

# --- Third-party imports ---
try:
    from dotenv import load_dotenv

    # Try multiple .env locations
    env_candidates = [project_root / ".env", project_root / "infrastructure" / ".env", src_path / ".env"]

    for env_file in env_candidates:
        if env_file.exists():
            load_dotenv(str(env_file), override=False)
            print(f"Loaded .env from: {env_file}")  # noqa: T201
            break
    else:
        print("No .env file found in candidate locations")  # noqa: T201

except ImportError:
    print("dotenv not available, skipping .env loading")  # noqa: T201

from alembic import context
from sqlalchemy import engine_from_config, pool

# --- Local application imports (after sys.path patch) ---
try:
    from src.backend.cc import mem0_models as mem0_models
    from src.backend.cc import models as cc_models  # noqa: F401
    from src.db.base import Base

    print("Successfully imported COS modules")  # noqa: T201
except ImportError as e:
    print(f"Import error: {e}")  # noqa: T201
    print(f"Current sys.path: {sys.path}")  # noqa: T201
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

print(f"Using migration URL: {migrate_url}")  # noqa: T201
config.set_main_option("sqlalchemy.url", migrate_url)

# --- Target metadata for autogenerate ---
target_metadata = Base.metadata

# --- filter so Alembic only watches our schemas ------------
WATCH_SCHEMAS = {"cc", "mem0_cc"}


def include_object(obj: object, name: str, type_: str, reflected: bool, compare_to: object) -> bool:
    if type_ == "table":
        return obj.schema in WATCH_SCHEMAS  # type: ignore[attr-defined]
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

# ruff: noqa: E402
