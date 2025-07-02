"""PostgreSQL-specific test fixtures with proper transaction isolation.

Based on SQLAlchemy async best practices for test transaction management.
Uses savepoint patterns for optimal test isolation.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.db.base import Base

# PostgreSQL test database URL as specified
POSTGRES_DEV_URL = "postgresql+asyncpg://cos_user:cos_dev_pass@localhost:5433/cos_db_dev"


@pytest_asyncio.fixture(scope="function")
async def postgres_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create async engine for PostgreSQL test database."""
    engine = create_async_engine(
        POSTGRES_DEV_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        echo=False,
    )

    # Run alembic upgrade head once per session
    async with engine.begin() as conn:
        # Import all models to ensure they're registered with Base.metadata
        from src.backend.cc import models  # noqa: F401

        # Create all tables - this replaces alembic for test simplicity
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def postgres_session(postgres_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide PostgreSQL session with proper transaction isolation.

    Uses nested transactions (savepoints) to ensure test isolation while
    maintaining the ability to test database constraints and rollbacks.

    Pattern based on SQLAlchemy documentation for testing with transactions:
    https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites
    """
    async with postgres_engine.connect() as conn:
        # Start outer transaction
        txn = await conn.begin()

        # Start nested transaction (savepoint) for test isolation
        await conn.begin_nested()

        # Create sessionmaker bound to this connection with create_savepoint mode
        # This allows ORM commits/rollbacks to use savepoints while preserving outer transaction
        sessionmaker_ = async_sessionmaker(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")

        async with sessionmaker_() as session:
            yield session

        # Rollback nested transaction (savepoint)
        await conn.rollback()

        # Rollback outer transaction
        await txn.rollback()


@pytest_asyncio.fixture
async def postgres_session_no_transaction(postgres_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide PostgreSQL session without transaction isolation.

    Useful for testing transaction behavior or when you need to commit changes.
    Remember to clean up manually in your test!
    """
    sessionmaker_ = async_sessionmaker(postgres_engine, expire_on_commit=False)

    async with sessionmaker_() as session:
        yield session
