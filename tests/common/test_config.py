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


def test_settings_missing_critical() -> None:
    """Test that Settings can be instantiated even with no environment variables.

    This test validates that all fields have defaults, which is intentional
    for development convenience but could be a security consideration.
    """
    import subprocess
    import sys
    from pathlib import Path

    # Run in subprocess to ensure clean environment and no .env loading
    code = """
import os
# Clear all environment variables related to our config
for key in list(os.environ.keys()):
    if key.startswith(('POSTGRES', 'REDIS', 'DATABASE', 'NEO4J', 'MEM0', 'ENV_FILE')):
        del os.environ[key]

# Prevent .env file loading by setting a non-existent ENV_FILE
os.environ['ENV_FILE'] = '/tmp/nonexistent.env'

# This should work because all fields have defaults
from src.common.config import Settings
s = Settings()

# Verify we got the hardcoded defaults, not .env values
assert s.POSTGRES_DEV_URL == "postgresql://test:test@localhost/test_db", f"Got: {s.POSTGRES_DEV_URL}"
assert s.REDIS_HOST == "localhost", f"Got: {s.REDIS_HOST}"
assert s.REDIS_PASSWORD == "test_password", f"Got: {s.REDIS_PASSWORD}"
assert s.MEM0_SCHEMA == "mem0_cc", f"Got: {s.MEM0_SCHEMA}"
assert s.NEO4J_URI == "bolt://localhost:7687", f"Got: {s.NEO4J_URI}"

print("SUCCESS: Settings created with all defaults")
"""

    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent),
    )

    assert result.returncode == 0, f"Subprocess failed: {result.stderr}"
    assert "SUCCESS" in result.stdout


def test_mem0_schema_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # Unset MEM0_SCHEMA if set
    monkeypatch.delenv("MEM0_SCHEMA", raising=False)
    s = Settings()
    assert s.MEM0_SCHEMA == "mem0_cc"


def test_mem0_schema_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEM0_SCHEMA", "custom_schema")
    s = Settings()
    assert s.MEM0_SCHEMA == "custom_schema"


def test_mem0_schema_type() -> None:
    s = Settings()
    assert isinstance(s.MEM0_SCHEMA, str)
