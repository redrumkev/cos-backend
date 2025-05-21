from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest


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
