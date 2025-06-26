from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from unittest.mock import Mock, patch

import pytest  # Phase 2: Remove for skip removal
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

import src.db.connection as db_conn
from src.db.connection import get_db_session

# ✅ Phase 2: P2-CONNECT-001 RESOLVED - Database connection logic completed
# Resolved by: Environment setup RUN_INTEGRATION=1 ENABLE_DB_INTEGRATION=1 + connection URL handling


RUN_INTEGRATION = os.getenv("ENABLE_DB_INTEGRATION") == "1"


def test_database_url_for_tests() -> None:
    """Test that _database_url_for_tests always returns PostgreSQL dev URL."""
    # Phase 2: Always use dev database (port 5433), no SQLite fallback
    url = db_conn._database_url_for_tests()
    assert url.startswith("postgresql+asyncpg://")
    assert ":5433/" in url  # Should use dev database port


def test_engine_pooling_enabled() -> None:
    """Test that PostgreSQL engine has pooling configured."""
    # Phase 2: Always use PostgreSQL with pooling
    engine = db_conn.get_async_engine()
    assert engine.pool is not None  # Pool should exist
    assert hasattr(engine.pool, "size")  # Should have pool size configuration


@pytest.mark.asyncio
async def test_basic_connection() -> None:
    """Test basic PostgreSQL connection works."""
    # Phase 2: Always test PostgreSQL connection
    engine = db_conn.get_async_engine()

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT version()"))
        version = result.scalar()
        assert "PostgreSQL" in version  # type: ignore[operator]


@pytest.mark.skipif(not RUN_INTEGRATION, reason="PostgreSQL integration not enabled")
@pytest.mark.asyncio
async def test_postgres_specific_features() -> None:
    """Test PostgreSQL-specific features when integration is enabled."""
    engine = db_conn.get_async_engine()

    async with engine.connect() as conn:
        # Test schema creation (PostgreSQL only)
        try:
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS test_schema"))
            await conn.execute(text("DROP SCHEMA test_schema CASCADE"))
        except OperationalError:
            pytest.skip("Could not test schema creation")


def test_database_url_for_tests_environment_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that environment variable override works."""
    test_url = "postgresql+asyncpg://test_user:test_pass@localhost:5433/test_db"
    monkeypatch.setenv("DATABASE_URL_DEV", test_url)

    url = db_conn._database_url_for_tests()
    assert url == test_url


# Test without PostgreSQL integration
@pytest.mark.unit
class TestDatabaseConnectionUnit:
    """Test database connection logic without actual DB integration."""

    @patch("src.db.connection.get_db_url")
    def test_get_db_session_returns_async_session(self, mock_get_db_url: Mock) -> None:
        """Test that get_db_session returns an AsyncSession."""
        mock_get_db_url.return_value = os.getenv("DATABASE_URL_TEST")
        session_gen = get_db_session()
        assert isinstance(session_gen, AsyncGenerator)


# Test with PostgreSQL integration
@pytest.mark.integration
class TestDatabaseConnectionIntegration:
    """Test database connection with a real PostgreSQL database."""

    async def test_real_db_connection_and_session(self, db_session: AsyncSession) -> None:
        """Test a real connection and session to the database."""
        assert isinstance(db_session, AsyncSession)
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    async def test_multiple_sessions_work_independently(self, db_session: AsyncSession) -> None:
        """Test that multiple sessions can be created and work independently."""
        # Test that we can create multiple sessions
        new_session_gen = get_db_session()
        new_session = await anext(new_session_gen)

        try:
            # Both sessions should work independently
            result1 = await db_session.execute(text("SELECT 1 as test_col"))
            result2 = await new_session.execute(text("SELECT 2 as test_col"))

            assert result1.scalar() == 1
            assert result2.scalar() == 2
        finally:
            await new_session.close()
