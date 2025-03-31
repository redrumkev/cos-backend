"""FastAPI dependencies for the Control Center module.

This file contains shared dependencies that can be used across router endpoints
such as database sessions, authentication, and configuration access.
"""

# MDC: cc_module
from collections.abc import AsyncGenerator
from typing import Annotated
from unittest.mock import AsyncMock

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import log_event


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for dependency injection.

    During testing and development, this returns a mock session.
    In production, this will return a real PostgreSQL connection.

    Yields:
        AsyncSession: SQLAlchemy async session or mock

    """
    log_event(
        source="cc",
        data={},
        tags=["dependency", "db_session"],
        memo="Database session requested (testing mode).",
    )

    # For testing purposes, yield a mock session
    # This approach lets tests run without database dependencies
    mock_session = AsyncMock(spec=AsyncSession)
    yield mock_session

    # When ready to implement real database:
    # async with async_session_maker() as session:
    #     yield session


# Common type annotations for cleaner route definitions
DBSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_module_config() -> dict[str, str]:
    """Get current CC module configuration for dependency injection.

    Returns:
        dict[str, str]: Module configuration

    """
    # Currently returning hardcoded config, will be replaced with actual config
    log_event(
        source="cc",
        data={},
        tags=["dependency", "config"],
        memo="Module configuration requested.",
    )
    return {
        "version": "0.1.0",
        "environment": "development",
    }


# Common type annotation for module config
ModuleConfig = Annotated[dict[str, str], Depends(get_module_config)]
