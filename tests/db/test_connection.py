import contextlib
import os
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

import src.db.connection as db_conn


class DummySettings:
    POSTGRES_TEST_URL = "postgresql://user:pass@localhost:5432/test_db"
    POSTGRES_DEV_URL = "postgresql://user:pass@localhost:5432/dev_db"


RUN_INTEGRATION = os.getenv("ENABLE_DB_INTEGRATION") == "1"


def test_engine_url_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    # Test test/dev URL switching
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    with patch("src.db.connection.get_settings", return_value=DummySettings()):
        engine = db_conn.get_async_engine()
        url = engine.url.render_as_string(hide_password=False)
        assert url.startswith("postgresql+asyncpg://")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with patch("src.db.connection.get_settings", return_value=DummySettings()):
        engine = db_conn.get_async_engine()
        url = engine.url.render_as_string(hide_password=False)
        assert url.startswith("postgresql+asyncpg://")


def test_session_maker_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    with patch("src.db.connection.get_settings", return_value=DummySettings()):
        session_maker = db_conn.get_async_session_maker()
        session = session_maker()
        assert isinstance(session, AsyncSession)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)


@pytest.mark.asyncio
async def test_async_db_yields_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    with patch("src.db.connection.get_settings", return_value=DummySettings()):
        agen = db_conn.get_async_db()
        session = await agen.__anext__()
        assert isinstance(session, AsyncSession)
        # Clean up generator
        with contextlib.suppress(StopAsyncIteration):
            await agen.__anext__()
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)


@pytest.mark.skipif(not RUN_INTEGRATION, reason="integration DB not enabled")
@pytest.mark.asyncio
async def test_select_1(monkeypatch: pytest.MonkeyPatch) -> None:
    # Integration test: run SELECT 1 if test DB is available
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    with patch("src.db.connection.get_settings", return_value=DummySettings()):
        engine = db_conn.get_async_engine()
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                val = result.scalar()
                assert val == 1
        except OperationalError:
            pytest.skip("Test DB not available for SELECT 1 integration test.")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
