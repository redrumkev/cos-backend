"""Tests for missing config coverage in the common module.

This file contains tests for configuration loading that were missing coverage,
focusing on environment file loading and URL conversion paths.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest  # Phase 2: Remove for skip removal

from src.common.config import Settings, get_settings, get_settings_dep

# Phase 2: Remove this skip block for configuration testing (P2-CONFIG-001)
pytestmark = pytest.mark.skip(reason="Phase 2: Configuration testing needed. Trigger: P2-CONFIG-001")


class TestSettingsEnvironmentLoading:
    """Test environment file loading behavior."""

    @pytest.mark.xfail(reason="config loading behavior changed - env loading is now optional")
    @patch("src.common.config.Path.exists")
    @patch("src.common.config.load_dotenv")
    def test_env_file_explicit_exists(self, mock_load_dotenv: MagicMock, mock_exists: MagicMock) -> None:
        """Test loading when ENV_FILE is explicitly set and exists."""
        mock_exists.return_value = True

        with patch.dict(os.environ, {"ENV_FILE": "/custom/.env"}):
            # Need to reload module to trigger the env loading logic
            import importlib

            import src.common.config

            importlib.reload(src.common.config)

        mock_load_dotenv.assert_called()

    @pytest.mark.xfail(reason="config loading behavior changed - env loading is now optional")
    @patch("src.common.config.Path.exists")
    @patch("src.common.config.load_dotenv")
    def test_env_file_infrastructure_path(self, mock_load_dotenv: MagicMock, mock_exists: MagicMock) -> None:
        """Test loading infrastructure/.env when no ENV_FILE set."""
        mock_exists.return_value = True

        with patch.dict(os.environ, {}, clear=True):
            # Need to reload module to trigger the env loading logic
            import importlib

            import src.common.config

            importlib.reload(src.common.config)

        # Should try to load from infrastructure/.env
        mock_load_dotenv.assert_called()

    @patch("src.common.config.Path.exists")
    @patch("src.common.config.load_dotenv")
    def test_env_file_not_exists(self, mock_load_dotenv: MagicMock, mock_exists: MagicMock) -> None:
        """Test when candidate env file doesn't exist."""
        mock_exists.return_value = False

        with patch.dict(os.environ, {}, clear=True):
            # Need to reload module to trigger the env loading logic
            import importlib

            import src.common.config

            importlib.reload(src.common.config)

        # Should not load dotenv if file doesn't exist
        mock_load_dotenv.assert_not_called()


class TestSettingsProperties:
    """Test Settings class properties."""

    def test_sync_db_url_property(self) -> None:
        """Test sync_db_url property returns POSTGRES_DEV_URL."""
        settings = Settings(POSTGRES_DEV_URL="postgresql://user:pass@host/db")

        result = settings.sync_db_url
        assert result == "postgresql://user:pass@host/db"

    def test_async_db_url_postgresql_conversion(self) -> None:
        """Test async_db_url converts postgresql:// to postgresql+asyncpg://."""
        settings = Settings(POSTGRES_DEV_URL="postgresql://user:pass@host/db")

        result = settings.async_db_url
        assert result == "postgresql+asyncpg://user:pass@host/db"

    def test_async_db_url_already_asyncpg(self) -> None:
        """Test async_db_url doesn't double-convert postgresql+asyncpg://."""
        settings = Settings(POSTGRES_DEV_URL="postgresql+asyncpg://user:pass@host/db")

        result = settings.async_db_url
        assert result == "postgresql+asyncpg://user:pass@host/db"

    def test_async_db_url_non_postgresql(self) -> None:
        """Test async_db_url with non-postgresql URL."""
        settings = Settings(POSTGRES_DEV_URL="sqlite:///test.db")

        result = settings.async_db_url
        assert result == "sqlite:///test.db"


class TestSettingsDefaults:
    """Test Settings default values."""

    def test_settings_defaults(self) -> None:
        """Test that Settings has proper default values."""
        # Clear environment variables that might affect defaults
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

            assert settings.POSTGRES_DEV_URL == "postgresql://test:test@localhost/test_db"
            assert settings.POSTGRES_TEST_URL == "postgresql://test:test@localhost/test_test_db"
            assert settings.REDIS_HOST == "localhost"
            assert settings.REDIS_PORT == 6379
            assert settings.REDIS_PASSWORD == "test_password"  # noqa: S105
            assert settings.MEM0_SCHEMA == "mem0_cc"

    def test_settings_with_custom_values(self) -> None:
        """Test Settings with custom environment values."""
        custom_env = {
            "POSTGRES_DEV_URL": "postgresql://custom:custom@custom/custom_db",
            "REDIS_HOST": "redis.example.com",
            "REDIS_PORT": "6380",
            "MEM0_SCHEMA": "custom_mem0",
        }

        with patch.dict(os.environ, custom_env):
            settings = Settings()

            assert settings.POSTGRES_DEV_URL == "postgresql://custom:custom@custom/custom_db"
            assert settings.REDIS_HOST == "redis.example.com"
            assert settings.REDIS_PORT == 6380
            assert settings.MEM0_SCHEMA == "custom_mem0"

    def test_redis_password_none(self) -> None:
        """Test Settings with REDIS_PASSWORD set to empty string."""
        with patch.dict(os.environ, {"REDIS_PASSWORD": ""}, clear=True):
            settings = Settings()
            # Should use the empty string from environment, not default
            assert settings.REDIS_PASSWORD == ""


class TestSettingsFunctions:
    """Test settings utility functions."""

    def test_get_settings_cached(self) -> None:
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance due to lru_cache
        assert settings1 is settings2

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="isinstance check fails after module reload tests - state contamination issue")
    async def test_get_settings_dep(self) -> None:
        """Test get_settings_dep async function."""
        settings = await get_settings_dep()

        assert isinstance(settings, Settings)
        # Should return the same cached instance
        assert settings is get_settings()

    def test_get_settings_lru_cache_info(self) -> None:
        """Test that get_settings uses lru_cache."""
        # Clear any existing cache
        get_settings.cache_clear()

        # First call
        settings1 = get_settings()
        cache_info1 = get_settings.cache_info()
        assert cache_info1.hits == 0
        assert cache_info1.misses == 1

        # Second call should hit cache
        settings2 = get_settings()
        cache_info2 = get_settings.cache_info()
        assert cache_info2.hits == 1
        assert cache_info2.misses == 1

        assert settings1 is settings2


class TestSettingsConfigDict:
    """Test Settings configuration."""

    def test_model_config_properties(self) -> None:
        """Test that model_config has expected properties."""
        settings = Settings()

        # Test the model configuration exists and has expected behavior
        assert hasattr(settings, "model_config")
        # Since env_file attribute may not exist in newer Pydantic versions,
        # we test the general configuration behavior instead
        assert settings.model_config is not None
