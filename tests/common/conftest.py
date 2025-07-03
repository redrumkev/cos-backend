from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from freezegun import freeze_time


@pytest.fixture
def mock_env_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock environment settings for tests."""
    monkeypatch.setenv("AGENT_DB_URL", "agent://localhost:8000/database")
    monkeypatch.setenv("AGENT_TEST_URL", "agent://localhost:8000/test-database")
    monkeypatch.setenv("AGENT_POOL_SIZE", "5")
    monkeypatch.setenv("AGENT_POOL_TIMEOUT", "30")
    monkeypatch.setenv("AGENT_POOL_MAX_OVERFLOW", "10")

    # Add PostgreSQL URLs for backward compatibility
    monkeypatch.setenv(
        "POSTGRES_DEV_URL",
        "postgresql+asyncpg://cos_user:Police9119!!Sql_dev@localhost:5433/cos_db_dev",
    )
    monkeypatch.setenv(
        "POSTGRES_TEST_URL",
        "postgresql+asyncpg://cos_user:Police9119!!Sql_test@localhost:5433/cos_db_test",
    )


@pytest.fixture
def mock_agent_client() -> Generator[AsyncMock, None, None]:
    """Mock the agent client for testing."""
    with patch("src.common.agent.get_agent_client") as mock:
        mock.return_value = AsyncMock()
        yield mock


@pytest.fixture(autouse=True)
def mock_redis_health_monitor() -> Generator[None, None, None]:
    """Mock Redis health monitor to avoid 60 second timeouts in tests."""
    with patch("src.common.redis_health_monitor.get_redis_health_monitor") as mock_get_monitor:
        # Create a mock that always reports Redis as healthy
        mock_monitor = AsyncMock()
        mock_monitor.check_health.return_value = True
        mock_monitor.is_redis_available = True
        mock_get_monitor.return_value = mock_monitor
        yield


@pytest.fixture
def fast_time(monkeypatch: pytest.MonkeyPatch) -> Generator[Any, None, None]:
    """Mock time operations to speed up circuit breaker tests.

    This fixture combines freezegun with asyncio.sleep mocking to eliminate
    real-time delays in tests while preserving circuit breaker logic.
    """
    import time as time_module

    with freeze_time() as frozen_datetime:
        # Create async sleep mock that advances frozen time
        async def mock_sleep(seconds: float) -> None:
            frozen_datetime.tick(seconds)
            return

        # Patch asyncio.sleep to use our mock
        monkeypatch.setattr("asyncio.sleep", mock_sleep)

        # Also need to patch time.time in the pubsub module
        monkeypatch.setattr("src.common.pubsub.time.time", time_module.time)

        yield frozen_datetime
