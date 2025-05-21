import os

import pytest

from src.common.config import Settings


@pytest.mark.usefixtures("mock_env_settings")
def test_settings_loads_from_env() -> None:
    s = Settings()
    assert s.POSTGRES_DEV_URL == "postgresql://test:test@localhost/test_db"
    assert s.POSTGRES_TEST_URL == "postgresql://test:test@localhost/test_test_db"
    assert s.REDIS_HOST == "localhost"
    assert s.REDIS_PORT == 6379
    expected_pw = os.environ.get("REDIS_PASSWORD", "test_password")
    assert expected_pw == s.REDIS_PASSWORD
    assert s.sync_db_url == s.POSTGRES_DEV_URL
    assert s.async_db_url.startswith("postgresql+asyncpg://")


@pytest.mark.usefixtures("mock_env_settings")
def test_settings_type_coercion() -> None:
    s = Settings()
    assert isinstance(s.REDIS_PORT, int)
    assert s.REDIS_PORT == 6379


@pytest.mark.skip(reason="Requires real environment setup to test validation failures")
def test_settings_missing_critical() -> None:
    from pydantic_core import ValidationError

    with pytest.raises(ValidationError):
        Settings()
