"""Test suite for Redis configuration module."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.common.redis_config import RedisConfig, get_redis_config


class TestRedisConfig:
    """Test Redis configuration class."""

    @pytest.fixture
    def clean_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Clear Redis-related environment variables."""
        redis_env_vars = [
            "REDIS_URL",
            "REDIS_HOST",
            "REDIS_PORT",
            "REDIS_PASSWORD",
            "REDIS_DB",
            "REDIS_MAX_CONNECTIONS",
            "REDIS_SOCKET_CONNECT_TIMEOUT",
            "REDIS_SOCKET_KEEPALIVE",
            "REDIS_RETRY_ON_TIMEOUT",
            "REDIS_HEALTH_CHECK_INTERVAL",
            "TESTING",
            "ENV",
        ]

        for var in redis_env_vars:
            monkeypatch.delenv(var, raising=False)

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear the LRU cache before each test to ensure environment changes are picked up."""
        get_redis_config.cache_clear()

    def test_redis_config_default_values(self) -> None:
        """Test Redis configuration with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = RedisConfig()

            assert config.redis_host == "localhost"
            assert config.redis_port == 6379
            assert config.redis_password is None
            assert config.redis_db == 0
            assert config.redis_max_connections == 20
            assert config.redis_socket_connect_timeout == 5
            assert config.redis_socket_keepalive is True
            assert config.redis_retry_on_timeout is True
            assert config.redis_health_check_interval == 30

    def test_redis_config_from_environment(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Redis configuration from environment variables."""
        monkeypatch.setenv("REDIS_HOST", "redis-server")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_PASSWORD", "test-secret-123")
        monkeypatch.setenv("REDIS_DB", "1")
        monkeypatch.setenv("REDIS_MAX_CONNECTIONS", "50")

        config = RedisConfig()

        assert config.redis_host == "redis-server"
        assert config.redis_port == 6380
        assert config.redis_password == "test-secret-123"
        assert config.redis_db == 1
        assert config.redis_max_connections == 50

    def test_redis_url_property_without_password(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Redis URL generation without password."""
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)

        config = RedisConfig()

        # Handle both formats - with or without database suffix
        assert config.redis_url in ["redis://localhost:6379/0", "redis://localhost:6379"]

    def test_redis_url_property_with_password(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Redis URL generation with password."""
        monkeypatch.setenv("REDIS_HOST", "redis-server")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_DB", "1")
        monkeypatch.setenv("REDIS_PASSWORD", "test-secret")

        config = RedisConfig()

        # Handle both formats - with or without database suffix
        assert config.redis_url in [
            "redis://:test-secret@redis-server:6380/1",
            "redis://:test-secret@redis-server:6380",
        ]

    def test_connection_pool_config_property(self, clean_env: None) -> None:
        """Test connection pool configuration dictionary."""
        config = RedisConfig()
        pool_config = config.connection_pool_config

        assert pool_config["max_connections"] == 20
        assert pool_config["socket_connect_timeout"] == 5
        assert pool_config["socket_keepalive"] is True
        assert pool_config["retry_on_timeout"] is True
        assert pool_config["health_check_interval"] == 30

    def test_is_development_property(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test development environment detection."""
        # Test development mode
        monkeypatch.setenv("REDIS_HOST", "localhost")
        config_dev = RedisConfig()
        assert config_dev.is_development is True

        # Test production mode
        monkeypatch.setenv("REDIS_HOST", "redis-prod.example.com")
        config_prod = RedisConfig()
        assert config_prod.is_development is False

    def test_redis_config_validation_negative_port(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation fails for negative port."""
        monkeypatch.setenv("REDIS_PORT", "-1")

        with pytest.raises(ValidationError) as exc_info:
            RedisConfig()

        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than_equal" for error in errors)

    def test_redis_config_validation_port_too_high(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation fails for port > 65535."""
        monkeypatch.setenv("REDIS_PORT", "70000")

        with pytest.raises(ValidationError) as exc_info:
            RedisConfig()

        errors = exc_info.value.errors()
        assert any(error["type"] == "less_than_equal" for error in errors)

    def test_redis_config_validation_negative_db(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation fails for negative database number."""
        monkeypatch.setenv("REDIS_DB", "-1")

        with pytest.raises(ValidationError) as exc_info:
            RedisConfig()

        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than_equal" for error in errors)

    def test_redis_config_validation_max_connections_too_low(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test validation fails for max_connections < 1."""
        monkeypatch.setenv("REDIS_MAX_CONNECTIONS", "0")

        with pytest.raises(ValidationError) as exc_info:
            RedisConfig()

        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than_equal" for error in errors)

    def test_redis_config_str_representation(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test string representation of Redis config."""
        monkeypatch.setenv("REDIS_HOST", "test-host")
        monkeypatch.setenv("REDIS_PORT", "6379")

        config = RedisConfig()
        str_repr = str(config)

        assert "test-host" in str_repr
        assert "6379" in str_repr

    @patch.dict(os.environ, {}, clear=True)
    def test_redis_config_no_environment_variables(self) -> None:
        """Test Redis config with no environment variables set."""
        config = RedisConfig()

        # Should use all defaults
        assert config.redis_host == "localhost"
        assert config.redis_port == 6379
        assert config.redis_password is None


class TestGetRedisConfig:
    """Test the get_redis_config function."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear the LRU cache before each test to ensure environment changes are picked up."""
        get_redis_config.cache_clear()

    def test_get_redis_config_returns_instance(self) -> None:
        """Test that get_redis_config returns a RedisConfig instance."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_redis_config()
            assert isinstance(config, RedisConfig)

    def test_get_redis_config_caching(self) -> None:
        """Test that get_redis_config returns the same instance (cached)."""
        with patch.dict(os.environ, {}, clear=True):
            config1 = get_redis_config()
            config2 = get_redis_config()

            # Should be the same instance due to @lru_cache
            assert config1 is config2

    @patch.dict(os.environ, {"REDIS_HOST": "cached-test"}, clear=False)
    def test_get_redis_config_with_environment(self) -> None:
        """Test get_redis_config with environment variables."""
        # Clear the cache first
        get_redis_config.cache_clear()

        config = get_redis_config()
        assert config.redis_host == "cached-test"


class TestRedisConfigIntegration:
    """Integration tests for Redis configuration."""

    @pytest.fixture
    def clean_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Clear Redis-related environment variables."""
        redis_env_vars = [
            "REDIS_URL",
            "REDIS_HOST",
            "REDIS_PORT",
            "REDIS_PASSWORD",
            "REDIS_DB",
            "REDIS_MAX_CONNECTIONS",
            "REDIS_SOCKET_CONNECT_TIMEOUT",
            "REDIS_SOCKET_KEEPALIVE",
            "REDIS_RETRY_ON_TIMEOUT",
            "REDIS_HEALTH_CHECK_INTERVAL",
            "TESTING",
            "ENV",
        ]

        for var in redis_env_vars:
            monkeypatch.delenv(var, raising=False)

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear the LRU cache before each test to ensure environment changes are picked up."""
        get_redis_config.cache_clear()

    def test_development_configuration_integration(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test complete development configuration."""
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)
        monkeypatch.setenv("REDIS_DB", "0")

        config = RedisConfig()

        assert config.is_development is True
        assert config.redis_url == "redis://localhost:6379/0"
        assert config.connection_pool_config["max_connections"] == 20

    def test_production_configuration_integration(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test complete production configuration."""
        monkeypatch.setenv("REDIS_HOST", "redis-prod.company.com")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_PASSWORD", "prod-secret")
        monkeypatch.setenv("REDIS_DB", "1")
        monkeypatch.setenv("REDIS_MAX_CONNECTIONS", "100")

        config = RedisConfig()

        assert config.is_development is False
        assert config.redis_url == "redis://:prod-secret@redis-prod.company.com:6380/1"
        assert config.connection_pool_config["max_connections"] == 100

    def test_config_with_all_environment_variables(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test configuration with all possible environment variables."""
        env_vars = {
            "REDIS_HOST": "env-redis",
            "REDIS_PORT": "6381",
            "REDIS_PASSWORD": "env-test-password",
            "REDIS_DB": "2",
            "REDIS_MAX_CONNECTIONS": "30",
            "REDIS_SOCKET_CONNECT_TIMEOUT": "10",
            "REDIS_SOCKET_KEEPALIVE": "false",
            "REDIS_RETRY_ON_TIMEOUT": "false",
            "REDIS_HEALTH_CHECK_INTERVAL": "60",
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        config = RedisConfig()

        assert config.redis_host == "env-redis"
        assert config.redis_port == 6381
        assert config.redis_password == "env-test-password"
        assert config.redis_db == 2
        assert config.redis_max_connections == 30
        assert config.redis_socket_connect_timeout == 10
        assert config.redis_socket_keepalive is False
        assert config.redis_retry_on_timeout is False
        assert config.redis_health_check_interval == 60
