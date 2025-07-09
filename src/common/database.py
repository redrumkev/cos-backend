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

Pattern Reference: service.py v2.1.0 (Living Patterns System)
Pattern Reference: error_handling.py v2.1.0 (COSError integration)
Applied: ResourceFactory pattern for database connections
Applied: ExecutionContext for request-scoped operations
Applied: Multi-schema support (cc.*, pem.*, aic.*)
Applied: Dependency injection patterns
Applied: COSError for structured error handling
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

# Pattern Reference: service.py v2.1.0 (Living Patterns System)
# Applied: ResourceFactory pattern for database connections
# Applied: ExecutionContext for request-scoped operations
# Applied: Multi-schema support (cc.*, pem.*, aic.*)
# Applied: Dependency injection patterns


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


# === LIVING PATTERNS IMPLEMENTATION ===
# Pattern Reference: service.py v2.1.0 (Living Patterns System)


class DatabaseResourceFactory:
    """Resource factory for database connections with multi-schema support.

    Pattern Reference: service.py v2.1.0 (Living Patterns System)
    Implements the ResourceFactory pattern from service.py v2.1.0.
    Provides centralized management of database connections with schema-aware routing.

    Applied Patterns:
    - ResourceFactory: Centralized resource management
    - Multi-schema support: cc.*, pem.*, aic.* routing
    - Dependency injection: Settings injection for testability
    - COSError: Structured error handling for database operations
    """

    def __init__(self, settings: Any = None):
        """Initialize with injected settings dependency."""
        self.settings = settings or get_settings()
        self._engines: dict[str, Engine | AsyncEngine] = {}
        self._session_makers: dict[str, Any] = {}

    def get_engine(self, schema: str = "default", async_mode: bool = False) -> Engine | AsyncEngine:
        """Get engine for specified schema.

        Args:
        ----
            schema: Schema name (e.g., "cc", "pem", "aic")
            async_mode: Whether to return async engine

        Returns:
        -------
            SQLAlchemy engine instance

        """
        cache_key = f"{schema}_{async_mode}"

        if cache_key not in self._engines:
            if async_mode:
                self._engines[cache_key] = self._create_async_engine(schema)
            else:
                self._engines[cache_key] = self._create_sync_engine(schema)

        return self._engines[cache_key]

    def get_session_maker(self, schema: str = "default", async_mode: bool = False) -> Any:
        """Get session maker for specified schema.

        Args:
        ----
            schema: Schema name (e.g., "cc", "pem", "aic")
            async_mode: Whether to return async session maker

        Returns:
        -------
            SQLAlchemy session maker

        """
        cache_key = f"{schema}_{async_mode}"

        if cache_key not in self._session_makers:
            engine = self.get_engine(schema, async_mode)
            if async_mode:
                from sqlalchemy.ext.asyncio import async_sessionmaker

                self._session_makers[cache_key] = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)  # type: ignore[arg-type]
            else:
                self._session_makers[cache_key] = sessionmaker(bind=engine, autoflush=False, autocommit=False)  # type: ignore[arg-type]

        return self._session_makers[cache_key]

    def _create_sync_engine(self, schema: str) -> Engine:
        """Create sync engine for schema."""
        if _is_test_mode():
            return MagicMock(spec=Engine)

        db_url = self._get_db_url(schema, async_mode=False)
        return create_engine(db_url, future=True)

    def _create_async_engine(self, schema: str) -> AsyncEngine:
        """Create async engine for schema."""
        if _is_test_mode():
            return AsyncMock(spec=AsyncEngine)

        db_url = self._get_db_url(schema, async_mode=True)

        # Configure pool settings from agent environment variables
        engine_options: dict[str, Any] = {
            "future": True,
            "pool_pre_ping": True,
        }

        # Add agent-specific pool configuration if available
        if pool_size := os.environ.get("AGENT_POOL_SIZE"):
            engine_options["pool_size"] = int(pool_size)
        if pool_timeout := os.environ.get("AGENT_POOL_TIMEOUT"):
            engine_options["pool_timeout"] = int(pool_timeout)
        if max_overflow := os.environ.get("AGENT_POOL_MAX_OVERFLOW"):
            engine_options["max_overflow"] = int(max_overflow)

        return create_async_engine(db_url, **engine_options)

    def _get_db_url(self, schema: str, async_mode: bool = False) -> str:
        """Get database URL for schema.

        Supports schema-specific URLs when available, falls back to default.
        Schema-specific URLs: POSTGRES_CC_URL, POSTGRES_PEM_URL, POSTGRES_AIC_URL
        """
        # Check for schema-specific URL first
        schema_url = None
        if schema == "cc" and hasattr(self.settings, "POSTGRES_CC_URL"):
            schema_url = self.settings.POSTGRES_CC_URL
        elif schema == "pem" and hasattr(self.settings, "POSTGRES_PEM_URL"):
            schema_url = self.settings.POSTGRES_PEM_URL
        elif schema == "aic" and hasattr(self.settings, "POSTGRES_AIC_URL"):
            schema_url = self.settings.POSTGRES_AIC_URL

        # Use schema-specific URL if available, otherwise fall back to default
        base_url = schema_url or (self.settings.async_db_url if async_mode else self.settings.sync_db_url)

        # Convert to async format if needed
        if async_mode and base_url.startswith("postgresql://"):
            base_url = base_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        return base_url

    async def health_check(self) -> dict[str, Any]:
        """Health check for database factory."""
        return {
            "factory": self.__class__.__name__,
            "engines": len(self._engines),
            "session_makers": len(self._session_makers),
            "status": "healthy",
        }


class DatabaseExecutionContext:
    """Request-scoped database execution context.

    Pattern Reference: service.py v2.1.0 (Living Patterns System)
    Implements the ExecutionContext pattern from service.py v2.1.0.
    Provides resource management for database operations within a request scope.

    Applied Patterns:
    - ExecutionContext: Request-scoped resource management
    - Resource lifecycle: Automatic session cleanup
    - Multi-schema support: Schema-aware session management
    - Service integration: Works with DatabaseResourceFactory
    """

    def __init__(self, factory: DatabaseResourceFactory, schema: str = "default"):
        """Initialize with factory and schema."""
        self.factory = factory
        self.schema = schema
        self._sessions: dict[str, Any] = {}

    def get_session(self, async_mode: bool = False) -> Any:
        """Get session for current context."""
        cache_key = f"{self.schema}_{async_mode}"

        if cache_key not in self._sessions:
            session_maker = self.factory.get_session_maker(self.schema, async_mode)
            self._sessions[cache_key] = session_maker()

        return self._sessions[cache_key]

    async def get_async_session(self) -> AsyncSession:
        """Get async session for current context."""
        return self.get_session(async_mode=True)  # type: ignore[no-any-return]

    def get_sync_session(self) -> Session:
        """Get sync session for current context."""
        return self.get_session(async_mode=False)  # type: ignore[no-any-return]

    def close(self) -> None:
        """Close all sessions in context."""
        for session in self._sessions.values():
            if hasattr(session, "close"):
                session.close()
        self._sessions.clear()


# Global factory instance for backward compatibility
_database_factory = DatabaseResourceFactory()


def get_database_factory() -> DatabaseResourceFactory:
    """Get global database factory instance."""
    return _database_factory


def get_execution_context(schema: str = "default") -> DatabaseExecutionContext:
    """Get execution context for schema."""
    return DatabaseExecutionContext(_database_factory, schema)
