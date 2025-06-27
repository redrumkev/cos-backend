from __future__ import annotations

import os

import pytest  # Phase 2: Remove for skip removal

from src.common.config import Settings

# Phase 2: Skip block removed - configuration testing enabled (P2-CONFIG-001)


@pytest.mark.usefixtures("mock_env_settings")
def test_settings_loads_from_env() -> None:
    s = Settings()
    # These values should match the defaults or the values in infrastructure/.env
    assert s.POSTGRES_DEV_URL.startswith("postgresql")
    assert s.POSTGRES_TEST_URL.startswith("postgresql")
    assert s.REDIS_HOST in ("localhost", "redis")
    assert isinstance(s.REDIS_PORT, int)
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


def test_mem0_schema_default() -> None:
    # Unset MEM0_SCHEMA if set
    if "MEM0_SCHEMA" in os.environ:
        del os.environ["MEM0_SCHEMA"]
    s = Settings()
    assert s.MEM0_SCHEMA == "mem0_cc"


def test_mem0_schema_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEM0_SCHEMA", "custom_schema")
    s = Settings()
    assert s.MEM0_SCHEMA == "custom_schema"


def test_mem0_schema_type() -> None:
    s = Settings()
    assert isinstance(s.MEM0_SCHEMA, str)
