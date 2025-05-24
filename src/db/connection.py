# src/db/connection.py

import os
from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from src.common.config import get_settings


def _database_url_for_tests() -> str:
    """Return DB url based on env.

    - Check DATABASE_URL override first (set by conftest.py)
    - With ENABLE_DB_INTEGRATION=1 -> real Postgres
    - Else -> in-memory SQLite (aiosqlite driver)
    """
    # First check for explicit DATABASE_URL override (used by conftest.py)
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"]

    if os.getenv("ENABLE_DB_INTEGRATION", "0") == "1":
        s = get_settings()
        in_test_mode = "PYTEST_CURRENT_TEST" in os.environ
        return s.POSTGRES_TEST_URL if in_test_mode else s.POSTGRES_DEV_URL
    return "sqlite+aiosqlite:///:memory:"


def _create_engine_impl(db_url: str) -> AsyncEngine:
    """Create the actual engine without caching."""
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if "postgresql" in db_url:
        # PostgreSQL configuration
        return create_async_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            echo=False,
        )
    else:
        # SQLite configuration (including aiosqlite)
        connect_args = {}
        if "sqlite" in db_url:
            connect_args = {"check_same_thread": False}

        return create_async_engine(
            db_url,
            connect_args=connect_args,
            echo=False,
        )


@lru_cache
def get_async_engine() -> AsyncEngine:
    """Get async engine, with caching disabled in test mode."""
    # In test mode, don't use cache to ensure fresh engines
    if "PYTEST_CURRENT_TEST" in os.environ:
        db_url = _database_url_for_tests()
        return _create_engine_impl(db_url)

    # Use cached version for production
    db_url = _database_url_for_tests()
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
