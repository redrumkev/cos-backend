# src/db/connection.py
"""Database connection management with enhanced patterns.

Pattern Reference: src/core_v2/patterns/database_operations.py v2025-07-18
Applied: Optimized connection pool configuration from DatabaseConfig
Applied: Circuit breaker protection for database connections
Applied: Modern SQLAlchemy 2.0+ async patterns
Applied: Health monitoring and connection lifecycle management

This module provides backward compatibility while leveraging enhanced patterns.
"""

import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import orjson
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.common.logger import get_logger
from src.core_v2.patterns.database_operations import (
    DatabaseConfig,
    circuit_breaker,
)

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
    """Actual engine creation logic with enhanced patterns."""
    # Use optimized configuration from database operations patterns
    engine_options = DatabaseConfig.get_engine_options()

    # Add orjson serialization for PostgreSQL JSONB compatibility
    engine_options.update(
        {
            "json_serializer": lambda obj: orjson.dumps(obj).decode(),
            "json_deserializer": orjson.loads,
            "future": True,
        }
    )

    return create_async_engine(db_url, **engine_options)


def get_async_engine() -> AsyncEngine:
    """Get async engine - ALWAYS uses dev database (port 5433)."""
    # FORCE dev database for all operations during Phase 2
    # Remove @lru_cache during Phase 2 to prevent connection string caching issues
    db_url = get_db_url(dev=True)
    return _create_engine_impl(db_url)


def get_async_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get session maker with enhanced patterns - removes @lru_cache during Phase 2 to prevent caching issues."""
    engine = get_async_engine()

    # Use optimized session configuration from patterns
    session_options = DatabaseConfig.get_session_options()

    maker = async_sessionmaker(engine, **session_options)
    return maker


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async_session = get_async_session_maker()
    async with async_session() as session:
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


async def get_connection_health() -> dict[str, Any]:
    """Get health status for database connections with circuit breaker information."""
    health_data = {
        "module": "db.connection",
        "status": "healthy",
        "circuit_breaker": {
            "state": circuit_breaker.state.value,
            "failure_count": circuit_breaker.failure_count,
            "last_failure_time": circuit_breaker.last_failure_time,
        },
    }

    try:
        # Test database connectivity
        session_maker = get_async_session_maker()
        async with session_maker() as session:
            # Simple connectivity test with circuit breaker protection
            test_query = "SELECT 1 as test"
            result = await circuit_breaker.call(session.execute, test_query)

            if result.scalar() == 1:
                health_data["database_connectivity"] = "ok"
            else:
                health_data["status"] = "unhealthy"
                health_data["error"] = "Failed to execute test query"

    except Exception as e:
        health_data["status"] = "unhealthy"
        health_data["error"] = str(e)

    return health_data
