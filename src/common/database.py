import os
from collections.abc import AsyncGenerator, Callable, Generator
from functools import lru_cache
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine  # Added Engine for type hinting
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from src.common.config import get_settings

# Check if we're in a test environment
IN_TEST_MODE = "PYTEST_CURRENT_TEST" in os.environ


@lru_cache
def get_engine() -> Engine | MagicMock:
    """Get SQLAlchemy sync engine with lazy initialization."""
    if IN_TEST_MODE:
        # For tests, return a mock engine to avoid requiring PostgreSQL drivers
        mock_engine = MagicMock(spec=Engine)
        return mock_engine

    settings = get_settings()
    return create_engine(settings.sync_db_url, future=True)


@lru_cache
def get_session_maker() -> Callable[..., Session | MagicMock]:
    """Get SQLAlchemy sync session maker with lazy initialization."""
    if IN_TEST_MODE:
        # For tests, create a session maker that returns a mock session
        def mock_session_factory(*args: Any, **kwargs: Any) -> MagicMock:
            mock_session = MagicMock(spec=Session)
            return mock_session

        return mock_session_factory

    return sessionmaker(bind=get_engine(), class_=Session, autoflush=False, autocommit=False)


@lru_cache
def get_async_engine() -> AsyncEngine | AsyncMock:
    """Get SQLAlchemy async engine with lazy initialization."""
    if IN_TEST_MODE:
        # For tests, return a mock engine to avoid requiring PostgreSQL drivers
        mock_engine = AsyncMock(spec=AsyncEngine)
        return mock_engine

    settings = get_settings()
    db_url = settings.POSTGRES_TEST_URL if IN_TEST_MODE else settings.async_db_url
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return create_async_engine(db_url, future=True)


@lru_cache
def get_async_session_maker() -> Callable[..., AsyncSession | AsyncMock]:
    """Get SQLAlchemy async session maker with lazy initialization."""
    if IN_TEST_MODE:

        class MockAsyncSession(AsyncMock, AsyncSession):
            """Mock class that inherits from both AsyncMock and AsyncSession."""

            async def __aenter__(self) -> "MockAsyncSession":
                """Return self when used as a context manager."""
                return self

        def mock_session_factory(*args: Any, **kwargs: Any) -> MockAsyncSession:
            return MockAsyncSession(spec=AsyncSession)

        # Create session_maker first with no arguments, then configure it
        return mock_session_factory
    # This avoids the type error with AsyncEngine
    session_maker = sessionmaker(autoflush=False, autocommit=False)
    session_maker.configure(bind=get_async_engine(), class_=AsyncSession)
    return cast(Callable[..., AsyncSession | AsyncMock], session_maker)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get a database session."""
    db_session_factory = get_session_maker()
    db = db_session_factory()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get an async database session."""
    async_session_factory = get_async_session_maker()
    async with async_session_factory() as session:
        yield session
