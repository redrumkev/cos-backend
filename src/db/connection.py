# src/db/connection.py

import os
from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Any

import orjson
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from src.common.logger import get_logger

logger = get_logger(__name__)


def get_db_url(testing: bool = False, dev: bool = False) -> str:
    """Get the appropriate database URL based on the environment.

    Priority:
    1. TESTING=true -> DATABASE_URL_TEST
    2. DEV=true -> DATABASE_URL_DEV
    3. Production -> DATABASE_URL.
    """
    if testing:
        db_url = os.getenv("DATABASE_URL_TEST")
        if not db_url:
            logger.error("DATABASE_URL_TEST is not set in a testing environment!")
            raise ValueError("DATABASE_URL_TEST must be set for testing.")
        return db_url

    env_url = os.getenv("DATABASE_URL_DEV") if dev else os.getenv("DATABASE_URL")
    if not env_url:
        logger.error("Database URL (DATABASE_URL or DATABASE_URL_DEV) is not set!")
        raise ValueError("A database URL must be configured.")
    return env_url


def _database_url_for_tests() -> str:
    """Get database URL specifically for test environments.

    This function is used by test files to get the appropriate test database URL.
    It follows the PostgreSQL-only approach and uses the DATABASE_URL_TEST environment variable.
    """
    # Always use PostgreSQL for tests in the new architecture
    test_url = os.getenv("DATABASE_URL_TEST")
    if test_url:
        return test_url

    # Fallback to a default PostgreSQL test URL if not set
    logger.warning("DATABASE_URL_TEST not set, using default PostgreSQL test URL")
    return "postgresql+asyncpg://postgres:test_password@localhost:5434/cos_test"


def _create_engine_impl(db_url: str) -> AsyncEngine:
    """Actual engine creation logic."""
    engine_options: dict[str, Any] = {
        "json_serializer": orjson.dumps,
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


@lru_cache
def get_async_engine() -> AsyncEngine:
    """Get async engine, with caching disabled in test mode."""
    # In test mode, don't use cache to ensure fresh engines
    if "PYTEST_CURRENT_TEST" in os.environ:
        db_url = get_db_url(testing=True)
        return _create_engine_impl(db_url)

    # Use cached version for production
    db_url = get_db_url()
    return _create_engine_impl(db_url)


@lru_cache
def get_async_session_maker() -> sessionmaker[Session]:
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
