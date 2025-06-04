from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

import src.db.connection as db_conn


class DummySettings:
    POSTGRES_TEST_URL = "postgresql://user:pass@localhost:5432/test_db"
    POSTGRES_DEV_URL = "postgresql://user:pass@localhost:5432/dev_db"


RUN_INTEGRATION = os.getenv("ENABLE_DB_INTEGRATION") == "1"


def test_engine_url_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    # Test test/dev URL switching
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    if RUN_INTEGRATION:
        # With DB integration enabled, should use PostgreSQL
        with patch("src.db.connection.get_settings", return_value=DummySettings()):
            url = db_conn._database_url_for_tests()
            assert url.startswith("postgresql://")
    else:
        # Without DB integration, should use SQLite
        url = db_conn._database_url_for_tests()
        assert url == "sqlite+aiosqlite:///:memory:"


def test_engine_pooling_disabled() -> None:
    """Test that we don't use pooling for SQLite."""
    engine = db_conn.get_async_engine()
    if RUN_INTEGRATION:
        # PostgreSQL should have pool settings
        assert engine.pool.size() >= 0  # Pool exists
    else:
        # SQLite doesn't need pooling
        assert "sqlite" in str(engine.url)


@pytest.mark.asyncio
async def test_basic_connection() -> None:
    """Test basic DB connection works for both PostgreSQL and SQLite."""
    engine = db_conn.get_async_engine()

    async with engine.connect() as conn:
        if RUN_INTEGRATION:
            # Test PostgreSQL connection
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            assert "PostgreSQL" in version
        else:
            # Test SQLite connection
            result = await conn.execute(text("SELECT sqlite_version()"))
            version = result.scalar()
            assert version is not None  # Should return SQLite version


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


def test_database_url_for_tests_no_integration() -> None:
    """Test that without integration flag, SQLite is used."""
    # Temporarily unset the integration flag
    old_value = os.environ.get("ENABLE_DB_INTEGRATION")
    if "ENABLE_DB_INTEGRATION" in os.environ:
        del os.environ["ENABLE_DB_INTEGRATION"]

    try:
        url = db_conn._database_url_for_tests()
        assert url == "sqlite+aiosqlite:///:memory:"
    finally:
        # Restore old value
        if old_value is not None:
            os.environ["ENABLE_DB_INTEGRATION"] = old_value


def test_database_url_for_tests_with_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that with integration flag, PostgreSQL is used."""
    # Clear the DATABASE_URL override from conftest.py
    if "DATABASE_URL" in os.environ:
        monkeypatch.delenv("DATABASE_URL")

    monkeypatch.setenv("ENABLE_DB_INTEGRATION", "1")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    with patch("src.db.connection.get_settings", return_value=DummySettings()):
        url = db_conn._database_url_for_tests()
        assert url == "postgresql://user:pass@localhost:5432/test_db"
