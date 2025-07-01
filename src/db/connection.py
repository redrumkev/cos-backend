# src/db/connection.py

import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import orjson
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from src.common.logger import get_logger

# Load environment from infrastructure/.env
_infrastructure_env = Path(__file__).parent.parent.parent / "infrastructure" / ".env"
if _infrastructure_env.exists():
    load_dotenv(_infrastructure_env, override=False)

logger = get_logger(__name__)


def get_db_url(testing: bool = False, dev: bool = True) -> str:
    """Get database URL - ALWAYS use dev database (port 5433) during Phase 2.

    CRITICAL: Port 5434 is FORBIDDEN. All connections go to cos_postgres_dev (port 5433).
    """
    # FORCE dev=True always during Phase 2 - eliminate port 5434 usage
    if testing or dev or os.getenv("TESTING"):
        # Even in testing mode, use dev database (port 5433)
        db_url = os.getenv("DATABASE_URL_DEV")
        if not db_url:
            logger.warning("DATABASE_URL_DEV not set, using default dev URL")
            return "postgresql+asyncpg://cos_user:cos_dev_pass@localhost:5433/cos_db_dev"
        return db_url

    # Production URL (not used in Phase 2)
    env_url = os.getenv("DATABASE_URL")
    if not env_url:
        logger.error("DATABASE_URL is not set!")
        raise ValueError("DATABASE_URL must be configured for production.")
    return env_url


def _database_url_for_tests() -> str:
    """Get database URL for test environments - FORCED to dev database (port 5433).

    CRITICAL: Port 5434 is ELIMINATED. All tests use cos_postgres_dev (port 5433).
    """
    # FORCE all tests to use dev database - NO port 5434 allowed
    dev_url = os.getenv("DATABASE_URL_DEV")
    if dev_url:
        return dev_url

    # Fallback to dev database URL - NO port 5434 EVER
    logger.warning("DATABASE_URL_DEV not set, using default dev URL for tests")
    return "postgresql+asyncpg://cos_user:cos_dev_pass@localhost:5433/cos_db_dev"


def _create_engine_impl(db_url: str) -> AsyncEngine:
    """Actual engine creation logic."""
    engine_options: dict[str, Any] = {
        # asyncpg JSON/JSONB codec expects *str* not *bytes*, so decode.
        "json_serializer": lambda obj: orjson.dumps(obj).decode(),
        "json_deserializer": orjson.loads,
    }

    # Use connection pooling for PostgreSQL
    engine_options.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 3600,
            "pool_pre_ping": True,
        }
    )

    return create_async_engine(db_url, **engine_options)


def get_async_engine() -> AsyncEngine:
    """Get async engine - ALWAYS uses dev database (port 5433)."""
    # FORCE dev database for all operations during Phase 2
    # Remove @lru_cache during Phase 2 to prevent connection string caching issues
    db_url = get_db_url(dev=True)
    return _create_engine_impl(db_url)


def get_async_session_maker() -> sessionmaker[Session]:
    """Get session maker - removes @lru_cache during Phase 2 to prevent caching issues."""
    engine = get_async_engine()
    maker: sessionmaker[Session] = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    return maker


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async_session = get_async_session_maker()
    async with async_session() as session:  # type: ignore
        try:
            yield session
        finally:
            await session.rollback()


# Backward compatibility function for tests
def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Backward compatibility function for get_async_db.

    Some tests expect this function to exist in connection.py.
    This is an alias to get_async_db for compatibility.
    """
    return get_async_db()
