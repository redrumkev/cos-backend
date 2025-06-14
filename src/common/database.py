"""Database connection and session management for the COS backend.

This module provides:
- Agent-based database connections
- Async session factories
- Connection pooling configuration
- Rich logging for database operations

For onboarding:
1. Ensure Agent is configured and running
2. Set up .env with agent connection URLs
3. Use get_async_session_maker() for async contexts
"""

import os
from collections.abc import AsyncGenerator, Callable, Generator
from functools import lru_cache
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from rich.console import Console
from rich.text import Text
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine  # Added Engine for type hinting
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from src.common.config import get_settings


# Check if we're in a test environment
# IN_TEST_MODE = "PYTEST_CURRENT_TEST" in os.environ
def _is_test_mode() -> bool:
    """Check if we're currently in test mode (dynamic check)."""
    return "PYTEST_CURRENT_TEST" in os.environ


console = Console()


@lru_cache
def get_engine() -> Engine | MagicMock:
    """Get SQLAlchemy sync engine with lazy initialization."""
    if _is_test_mode():
        # For tests, return a mock engine to avoid requiring PostgreSQL drivers
        mock_engine = MagicMock(spec=Engine)
        return mock_engine

    settings = get_settings()
    return create_engine(settings.sync_db_url, future=True)


@lru_cache
def get_session_maker() -> Callable[..., Session | MagicMock]:
    """Get SQLAlchemy sync session maker with lazy initialization."""
    if _is_test_mode():
        # For tests, create a session maker that returns a mock session
        def mock_session_factory(*args: Any, **kwargs: Any) -> MagicMock:
            mock_session = MagicMock(spec=Session)
            return mock_session

        return mock_session_factory

    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


@lru_cache
def get_async_engine() -> AsyncEngine | AsyncMock:
    """Get SQLAlchemy async engine with lazy initialization."""
    if _is_test_mode():
        # For tests, return a mock engine to avoid requiring PostgreSQL drivers
        mock_engine = AsyncMock(spec=AsyncEngine)
        return mock_engine

    try:
        settings = get_settings()
        db_url = settings.POSTGRES_TEST_URL if _is_test_mode() else settings.async_db_url
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Configure pool settings from agent environment variables
        engine_options: dict[str, Any] = {
            "future": True,
            "pool_pre_ping": True,  # Always enable pre-ping for agent connections
        }

        # Add agent-specific pool configuration if available
        if pool_size := os.environ.get("AGENT_POOL_SIZE"):
            engine_options["pool_size"] = int(pool_size)
        if pool_timeout := os.environ.get("AGENT_POOL_TIMEOUT"):
            engine_options["pool_timeout"] = int(pool_timeout)
        if max_overflow := os.environ.get("AGENT_POOL_MAX_OVERFLOW"):
            engine_options["max_overflow"] = int(max_overflow)

        return create_async_engine(db_url, **engine_options)
    except Exception as e:
        console.print(Text(f"❌ Async engine initialization failed: {e}", style="red"))
        raise


@lru_cache
def get_async_session_maker() -> Callable[..., AsyncSession | AsyncMock]:
    """Get SQLAlchemy async session maker with lazy initialization."""
    if _is_test_mode():

        class MockAsyncSession(AsyncMock, AsyncSession):
            """Mock class that inherits from both AsyncMock and AsyncSession."""

            async def __aenter__(self) -> "MockAsyncSession":
                """Return self when used as a context manager."""
                return self

        def mock_session_factory(*args: Any, **kwargs: Any) -> MockAsyncSession:
            return MockAsyncSession(spec=AsyncSession)

        return mock_session_factory

    try:
        # Use async_sessionmaker for proper AsyncSession creation
        from sqlalchemy.ext.asyncio import async_sessionmaker

        return async_sessionmaker(get_async_engine(), expire_on_commit=False, autoflush=False)
    except Exception as e:
        console.print(Text(f"❌ Async session maker initialization failed: {e}", style="red"))
        raise


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
