"""Database Mock Chain Helper Foundation for COS tests.

This module provides standardized database mocking utilities to fix database
mock chain issues across the test suite. It handles the complex dependency
injection patterns used in the router pattern implementation.

Key Features:
- Standardized database override for FastAPI dependency injection
- ModuleDeps mock creation with proper database session handling
- Backward compatibility for async session maker patterns
- Context manager for test database setup and teardown
- Type-safe mock creation with proper typing hints

Usage:
    # Basic database override
    with test_db_context(app, mock_session) as session:
        # Test code here
        pass

    # ModuleDeps mock creation
    mock_deps = create_module_deps_mock(db_session=mock_session)
    result = await router_function(mock_deps)

    # Legacy async session maker override
    mock_session = create_async_session_maker_override(app)
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.config import Settings, get_settings
from src.common.database import get_async_db, get_async_session_maker
from src.core_v2.patterns.router import ModuleDeps
from src.graph.registry import ModuleLabel


def create_test_db_override(
    app: Any,
    mock_db_session: AsyncSession | MagicMock | None = None,
) -> AsyncSession | MagicMock:
    """Create standardized database override for FastAPI dependency injection.

    This function provides a standardized way to override the database dependency
    in FastAPI tests, ensuring consistent behavior across all test files.

    Args:
    ----
        app: FastAPI application instance
        mock_db_session: Optional mock database session. If None, creates a new MagicMock.

    Returns:
    -------
        The mock database session that was set up

    Example:
    -------
        mock_session = create_test_db_override(app, mock_db_session)
        # Now all routes will use mock_session instead of real database

    """
    if mock_db_session is None:
        mock_db_session = MagicMock(spec=AsyncSession)

    # Override the async database dependency
    app.dependency_overrides[get_async_db] = lambda: mock_db_session

    return mock_db_session


def create_async_session_maker_override(
    app: Any,
    mock_session: Any = None,
) -> Any:
    """Create backward compatibility override for async session maker.

    This function provides backward compatibility for tests that expect
    the older async session maker pattern.

    Args:
    ----
        app: FastAPI application instance
        mock_session: Optional mock session. If None, creates a new MagicMock.

    Returns:
    -------
        The mock session that was set up

    Example:
    -------
        mock_session = create_async_session_maker_override(app)
        # Now session maker calls will use mock_session

    """
    if mock_session is None:
        mock_session = MagicMock()

    # Override the async session maker dependency
    app.dependency_overrides[get_async_session_maker] = lambda: mock_session

    return mock_session


@contextmanager
def test_db_context(
    app: Any,
    mock_session: AsyncSession | MagicMock | None = None,
) -> Generator[AsyncSession | MagicMock, None, None]:
    """Context manager for test database setup and teardown.

    This context manager provides a clean way to set up database mocks
    for testing and ensures proper cleanup afterward.

    Args:
    ----
        app: FastAPI application instance
        mock_session: Optional mock database session

    Yields:
    ------
        The mock database session

    Example:
    -------
        with test_db_context(app, mock_session) as session:
            # Test code here
            response = await client.get("/endpoint")
            # Session is automatically cleaned up

    """
    session = create_test_db_override(app, mock_session)
    try:
        yield session
    finally:
        # Clear all dependency overrides to prevent test interference
        app.dependency_overrides.clear()


def create_module_deps_mock(
    module: ModuleLabel = ModuleLabel.TECH_CC,
    request: Request | None = None,
    db_session: AsyncSession | MagicMock | None = None,
    settings: Settings | None = None,
    background_tasks: BackgroundTasks | None = None,
    request_id: str | None = None,
) -> ModuleDeps:
    """Create a properly mocked ModuleDeps instance for direct function testing.

    This function creates a ModuleDeps instance with mocked dependencies,
    which is essential for testing router functions that use the new
    dependency injection pattern.

    Args:
    ----
        module: Module label for the dependencies
        request: Optional request object (will create mock if None)
        db_session: Optional database session (will create mock if None)
        settings: Optional settings object (will create mock if None)
        background_tasks: Optional background tasks (will create mock if None)
        request_id: Optional request ID (will generate if None)

    Returns:
    -------
        ModuleDeps instance with mocked dependencies

    Example:
    -------
        mock_deps = create_module_deps_mock(db_session=mock_db)
        result = await health_check(mock_deps)

    """
    if request is None:
        request = MagicMock(spec=Request)

    if db_session is None:
        db_session = MagicMock(spec=AsyncSession)

    if settings is None:
        settings = MagicMock(spec=Settings)

    if background_tasks is None:
        background_tasks = MagicMock(spec=BackgroundTasks)

    if request_id is None:
        request_id = "test-request-id"

    return ModuleDeps(
        module=module,
        request=request,
        db=db_session,
        settings=settings,
        background_tasks=background_tasks,
        request_id=request_id,
    )


def create_async_mock_db() -> AsyncMock:
    """Create a properly configured async mock database session.

    This function creates an AsyncMock configured specifically for database
    operations, with proper async/await support and common database methods.

    Returns:
    -------
        AsyncMock configured for database operations

    Example:
    -------
        mock_db = create_async_mock_db()
        mock_db.execute.return_value = mock_result
        mock_db.commit.return_value = None

    """
    mock_db = AsyncMock(spec=AsyncSession)

    # Configure common database operations
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_db.close = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()  # Not async
    mock_db.add_all = MagicMock()  # Not async
    mock_db.delete = MagicMock()  # Not async
    mock_db.query = MagicMock()  # Not async

    return mock_db


def create_fastapi_test_overrides(
    db_session: AsyncSession | MagicMock | None = None,
    settings: Settings | None = None,
) -> dict[Any, Any]:
    """Create a dictionary of FastAPI dependency overrides for testing.

    This function creates a comprehensive set of dependency overrides
    that can be applied to FastAPI test applications.

    Args:
    ----
        db_session: Optional database session override
        settings: Optional settings override

    Returns:
    -------
        Dictionary of dependency overrides

    Example:
    -------
        overrides = create_fastapi_test_overrides(mock_db, mock_settings)
        for dep, override in overrides.items():
            app.dependency_overrides[dep] = override

    """
    overrides: dict[Any, Any] = {}

    if db_session is not None:
        overrides[get_async_db] = lambda: db_session
        overrides[get_async_session_maker] = lambda: db_session

    if settings is not None:
        overrides[get_settings] = lambda: settings

    return overrides


@contextmanager
def mock_module_deps_context(
    module: ModuleLabel = ModuleLabel.TECH_CC,
    db_session: AsyncSession | MagicMock | None = None,
    **kwargs: Any,
) -> Generator[ModuleDeps, None, None]:
    """Context manager for module dependencies mocking.

    This context manager provides a clean way to create and manage
    ModuleDeps mocks for testing.

    Args:
    ----
        module: Module label for the dependencies
        db_session: Optional database session
        **kwargs: Additional arguments for ModuleDeps creation

    Yields:
    ------
        ModuleDeps instance with mocked dependencies

    Example:
    -------
        with mock_module_deps_context(db_session=mock_db) as deps:
            result = await router_function(deps)

    """
    deps = create_module_deps_mock(
        module=module,
        db_session=db_session,
        **kwargs,
    )
    try:
        yield deps
    finally:
        # Clean up any resources if needed
        pass


# Helper functions for specific test scenarios
def create_health_check_mock_db() -> MagicMock:
    """Create a mock database session configured for health check tests.

    Returns
    -------
        MagicMock configured for health check operations

    """
    mock_db = MagicMock(spec=AsyncSession)

    # Configure for health check specific operations
    mock_db.execute = AsyncMock()
    mock_db.scalar = AsyncMock()

    return mock_db


def create_crud_mock_db() -> MagicMock:
    """Create a mock database session configured for CRUD operations.

    Returns
    -------
        MagicMock configured for CRUD operations

    """
    mock_db = MagicMock(spec=AsyncSession)

    # Configure for CRUD operations
    mock_db.execute = AsyncMock()
    mock_db.scalar = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.delete = MagicMock()
    mock_db.refresh = AsyncMock()

    return mock_db


# Type aliases for better type hints
TestDatabase = AsyncSession | MagicMock
TestDependencyOverrides = dict[Any, Any]

# Export commonly used items
__all__ = [
    "TestDatabase",
    "TestDependencyOverrides",
    "create_async_mock_db",
    "create_async_session_maker_override",
    "create_crud_mock_db",
    "create_fastapi_test_overrides",
    "create_health_check_mock_db",
    "create_module_deps_mock",
    "create_test_db_override",
    "mock_module_deps_context",
    "test_db_context",
]
