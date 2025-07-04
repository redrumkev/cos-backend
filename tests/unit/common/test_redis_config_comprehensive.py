# Test file - configured per-file ignores in ruff.toml handle common test patterns
"""Redis configuration comprehensive testing.

This module provides comprehensive testing for Redis configuration
with various environment setups, edge cases, and integration scenarios.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.common.redis_config import RedisConfig, get_redis_config, get_redis_config_dep


class TestRedisConfigComprehensive:
    """Comprehensive Redis configuration testing with environment variables."""

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

    def test_default_initialization(self) -> None:
        """Test RedisConfig with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = RedisConfig()

            # Check default values
            assert config.redis_host == "localhost"
            assert config.redis_port == 6379
            assert config.redis_password is None
            assert config.redis_db == 0
            assert config.redis_max_connections == 20
            assert config.redis_socket_connect_timeout == 5
            assert config.redis_socket_keepalive is True
            assert config.redis_retry_on_timeout is True
            assert config.redis_health_check_interval == 30

    def test_custom_initialization(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test RedisConfig with custom environment variables."""
        monkeypatch.setenv("REDIS_HOST", "custom-redis")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_PASSWORD", "custom-password")
        monkeypatch.setenv("REDIS_DB", "2")
        monkeypatch.setenv("REDIS_MAX_CONNECTIONS", "50")
        monkeypatch.setenv("REDIS_SOCKET_CONNECT_TIMEOUT", "10")
        monkeypatch.setenv("REDIS_SOCKET_KEEPALIVE", "false")
        monkeypatch.setenv("REDIS_RETRY_ON_TIMEOUT", "false")
        monkeypatch.setenv("REDIS_HEALTH_CHECK_INTERVAL", "60")

        config = RedisConfig()

        assert config.redis_host == "custom-redis"
        assert config.redis_port == 6380
        assert config.redis_password == "custom-password"
        assert config.redis_db == 2
        assert config.redis_max_connections == 50
        assert config.redis_socket_connect_timeout == 10
        assert config.redis_socket_keepalive is False
        assert config.redis_retry_on_timeout is False
        assert config.redis_health_check_interval == 60

    def test_redis_url_without_password(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Redis URL generation without password."""
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)

        config = RedisConfig()
        expected_url = "redis://localhost:6379/0"

        assert config.redis_url == expected_url

    def test_redis_url_with_password(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Redis URL generation with password."""
        monkeypatch.setenv("REDIS_HOST", "redis.example.com")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_DB", "1")
        monkeypatch.setenv("REDIS_PASSWORD", "secret123")

        config = RedisConfig()
        expected_url = "redis://:secret123@redis.example.com:6380/1"

        assert config.redis_url == expected_url

    def test_redis_url_with_special_characters(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Redis URL generation with special characters in password."""
        monkeypatch.setenv("REDIS_HOST", "redis.example.com")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("REDIS_PASSWORD", "pass@word!#$%")

        config = RedisConfig()
        expected_url = "redis://:pass%40word%21%23%24%25@redis.example.com:6379/0"

        assert config.redis_url == expected_url

    def test_connection_pool_config_property(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test connection pool configuration dictionary generation."""
        monkeypatch.setenv("REDIS_MAX_CONNECTIONS", "30")
        monkeypatch.setenv("REDIS_SOCKET_CONNECT_TIMEOUT", "8")
        monkeypatch.setenv("REDIS_SOCKET_KEEPALIVE", "false")
        monkeypatch.setenv("REDIS_RETRY_ON_TIMEOUT", "true")
        monkeypatch.setenv("REDIS_HEALTH_CHECK_INTERVAL", "45")

        config = RedisConfig()
        pool_config = config.connection_pool_config

        expected_config = {
            "max_connections": 30,
            "socket_connect_timeout": 8,
            "socket_keepalive": False,
            "retry_on_timeout": True,
            "health_check_interval": 45,
        }

        assert pool_config == expected_config

    def test_is_development_property(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test development environment detection."""
        # Test localhost (development)
        monkeypatch.setenv("REDIS_HOST", "localhost")
        config_dev = RedisConfig()
        assert config_dev.is_development is True

        # Test 127.0.0.1 (development)
        monkeypatch.setenv("REDIS_HOST", "127.0.0.1")
        config_dev2 = RedisConfig()
        assert config_dev2.is_development is True

        # Test production host
        monkeypatch.setenv("REDIS_HOST", "redis-prod.company.com")
        config_prod = RedisConfig()
        assert config_prod.is_development is False

        # Test IP address (production)
        monkeypatch.setenv("REDIS_HOST", "10.0.1.100")
        config_prod2 = RedisConfig()
        assert config_prod2.is_development is False

    def test_str_representation(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test string representation of RedisConfig."""
        monkeypatch.setenv("REDIS_HOST", "test-redis-server")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_DB", "2")

        config = RedisConfig()
        str_repr = str(config)

        assert "test-redis-server" in str_repr
        assert "6380" in str_repr
        assert "2" in str_repr
        assert "RedisConfig" in str_repr

    def test_port_validation_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test port validation with negative values."""
        monkeypatch.setenv("REDIS_PORT", "-1")

        with pytest.raises(ValidationError) as exc_info:
            RedisConfig()

        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than_equal" for error in errors)

    def test_port_validation_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test port validation with zero."""
        monkeypatch.setenv("REDIS_PORT", "0")

        with pytest.raises(ValidationError) as exc_info:
            RedisConfig()

        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than_equal" for error in errors)

    def test_port_validation_too_high(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test port validation with values above 65535."""
        test_cases = ["65536", "70000", "100000"]

        for port in test_cases:
            monkeypatch.setenv("REDIS_PORT", port)

            with pytest.raises(ValidationError) as exc_info:
                RedisConfig()

            errors = exc_info.value.errors()
            assert any(error["type"] == "less_than_equal" for error in errors)

    def test_port_validation_valid_ranges(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test port validation with valid port ranges."""
        valid_ports = ["1", "80", "6379", "8080", "65535"]

        for port in valid_ports:
            monkeypatch.setenv("REDIS_PORT", port)

            # Should not raise exception
            config = RedisConfig()
            assert config.redis_port == int(port)

    def test_db_validation_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test database number validation with negative values."""
        monkeypatch.setenv("REDIS_DB", "-1")

        with pytest.raises(ValidationError) as exc_info:
            RedisConfig()

        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than_equal" for error in errors)

    def test_db_validation_valid_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test database number validation with valid values."""
        valid_dbs = ["0", "1", "15", "100"]

        for db in valid_dbs:
            monkeypatch.setenv("REDIS_DB", db)

            config = RedisConfig()
            assert config.redis_db == int(db)

    def test_max_connections_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test max connections validation."""
        # Test invalid values
        invalid_values = ["0", "-1", "-10"]

        for value in invalid_values:
            monkeypatch.setenv("REDIS_MAX_CONNECTIONS", value)

            with pytest.raises(ValidationError) as exc_info:
                RedisConfig()

            errors = exc_info.value.errors()
            assert any(error["type"] == "greater_than_equal" for error in errors)

        # Test valid values
        valid_values = ["1", "10", "100", "1000"]

        for value in valid_values:
            monkeypatch.setenv("REDIS_MAX_CONNECTIONS", value)

            config = RedisConfig()
            assert config.redis_max_connections == int(value)

    def test_socket_connect_timeout_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test socket connect timeout validation."""
        # Test invalid values
        invalid_values = ["0", "-1"]

        for value in invalid_values:
            monkeypatch.setenv("REDIS_SOCKET_CONNECT_TIMEOUT", value)

            with pytest.raises(ValidationError) as exc_info:
                RedisConfig()

            errors = exc_info.value.errors()
            assert any(error["type"] == "greater_than_equal" for error in errors)

    def test_health_check_interval_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test health check interval validation."""
        # Test invalid values
        invalid_values = ["0", "-1"]

        for value in invalid_values:
            monkeypatch.setenv("REDIS_HEALTH_CHECK_INTERVAL", value)

            with pytest.raises(ValidationError) as exc_info:
                RedisConfig()

            errors = exc_info.value.errors()
            assert any(error["type"] == "greater_than_equal" for error in errors)

    def test_boolean_field_parsing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test boolean field parsing from environment variables."""
        # Test various boolean representations
        boolean_tests = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
        ]

        for env_value, expected in boolean_tests:
            monkeypatch.setenv("REDIS_SOCKET_KEEPALIVE", env_value)

            config = RedisConfig()
            assert config.redis_socket_keepalive is expected

    def test_invalid_field_types(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation with invalid field types."""
        # Test non-numeric port
        monkeypatch.setenv("REDIS_PORT", "not-a-number")

        with pytest.raises(ValidationError):
            RedisConfig()

        # Test non-numeric db
        monkeypatch.setenv("REDIS_PORT", "6379")  # Reset port
        monkeypatch.setenv("REDIS_DB", "not-a-number")

        with pytest.raises(ValidationError):
            RedisConfig()

    @patch.dict(os.environ, {}, clear=True)
    def test_no_environment_variables(self) -> None:
        """Test RedisConfig with no environment variables set."""
        config = RedisConfig()

        # Should use all default values
        assert config.redis_host == "localhost"
        assert config.redis_port == 6379
        assert config.redis_password is None
        assert config.redis_db == 0
        assert config.redis_max_connections == 20

    def test_partial_environment_configuration(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test RedisConfig with partial environment configuration."""
        # Set only some environment variables
        monkeypatch.setenv("REDIS_HOST", "custom-redis")
        monkeypatch.setenv("REDIS_PASSWORD", "secret")
        # Leave other values as defaults

        config = RedisConfig()

        assert config.redis_host == "custom-redis"
        assert config.redis_password == "secret"
        assert config.redis_port == 6379  # Default
        assert config.redis_db == 0  # Default
        assert config.redis_max_connections == 20  # Default

    def test_computed_fields_are_not_settable(self) -> None:
        """Test that computed fields cannot be set directly."""
        config = RedisConfig()

        # These should be computed properties, not settable
        with pytest.raises(AttributeError):
            config.redis_url = "redis://custom:6379"  # type: ignore

        with pytest.raises(AttributeError):
            config.connection_pool_config = {}  # type: ignore

        with pytest.raises(AttributeError):
            config.is_development = True  # type: ignore

    def test_extra_fields_forbidden(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that extra fields are forbidden."""
        monkeypatch.setenv("REDIS_UNKNOWN_SETTING", "value")

        # Should not raise error - extra env vars are ignored
        config = RedisConfig()
        assert not hasattr(config, "redis_unknown_setting")

    def test_env_file_loading_simulation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test environment file loading simulation."""
        # Mock environment file path
        mock_env_path = "/fake/path/.env"
        monkeypatch.setenv("ENV_FILE", mock_env_path)

        # Mock Path.exists to return True
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("src.common.redis_config.load_dotenv") as mock_load_dotenv,
        ):
            # Creating instance should trigger dotenv loading
            from src.common.redis_config import RedisConfig

            _ = RedisConfig()

            # Should have attempted to load the env file
            mock_load_dotenv.assert_called()

    def test_dotenv_not_available_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fallback when python-dotenv is not available."""
        # Clear any environment variables that might be set by xdist
        monkeypatch.delenv("REDIS_HOST", raising=False)
        # Test that the module still works when dotenv import fails
        with patch.dict("sys.modules", {"dotenv": None}):
            # Should not raise ImportError
            config = RedisConfig()
            assert config.redis_host == "localhost"


class TestGetRedisConfig:
    """Test suite for get_redis_config function."""

    def test_get_redis_config_returns_instance(self) -> None:
        """Test that get_redis_config returns RedisConfig instance."""
        config = get_redis_config()
        assert isinstance(config, RedisConfig)

    def test_get_redis_config_caching(self) -> None:
        """Test that get_redis_config returns cached instance."""
        config1 = get_redis_config()
        config2 = get_redis_config()

        # Should be the same instance due to @lru_cache
        assert config1 is config2

    def test_get_redis_config_cache_clear(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test cache clearing functionality."""
        # Set environment variable
        monkeypatch.setenv("REDIS_HOST", "cache-test-host")

        # Clear cache to ensure fresh instance
        get_redis_config.cache_clear()

        config = get_redis_config()
        assert config.redis_host == "cache-test-host"

    def test_get_redis_config_with_environment_changes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_redis_config with environment variable changes."""
        # First configuration
        monkeypatch.setenv("REDIS_HOST", "first-host")
        get_redis_config.cache_clear()
        config1 = get_redis_config()

        # Change environment (but cache should return same instance)
        monkeypatch.setenv("REDIS_HOST", "second-host")
        config2 = get_redis_config()

        # Should still be the same instance (cached)
        assert config1 is config2
        assert config1.redis_host == "first-host"

        # Clear cache and get new instance
        get_redis_config.cache_clear()
        config3 = get_redis_config()

        # Now should be different instance with new environment
        assert config3 is not config1
        assert config3.redis_host == "second-host"

    def test_get_redis_config_thread_safety(self) -> None:
        """Test get_redis_config thread safety with caching."""
        import threading

        configs = []

        def get_config() -> None:
            configs.append(get_redis_config())

        # Create multiple threads to test concurrent access
        threads = [threading.Thread(target=get_config) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All should be the same instance
        assert len(configs) == 10
        assert all(config is configs[0] for config in configs)


class TestGetRedisConfigDep:
    """Test suite for get_redis_config_dep FastAPI dependency."""

    async def test_get_redis_config_dep_returns_instance(self) -> None:
        """Test that get_redis_config_dep returns RedisConfig instance."""
        config = await get_redis_config_dep()
        assert isinstance(config, RedisConfig)

    async def test_get_redis_config_dep_uses_cached_instance(self) -> None:
        """Test that dependency uses cached instance."""
        config1 = await get_redis_config_dep()
        config2 = await get_redis_config_dep()

        # Should be the same instance (uses get_redis_config internally)
        assert config1 is config2

    async def test_get_redis_config_dep_consistency(self) -> None:
        """Test consistency between dependency and direct function call."""
        config_direct = get_redis_config()
        config_dep = await get_redis_config_dep()

        # Should be the same instance
        assert config_direct is config_dep


class TestRedisConfigIntegrationScenarios:
    """Integration test scenarios for RedisConfig."""

    def test_development_environment_complete(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test complete development environment configuration."""
        # Typical development environment
        env_vars = {
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_DB": "0",
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)

        config = RedisConfig()

        assert config.is_development is True
        assert config.redis_url == "redis://localhost:6379/0"
        assert config.connection_pool_config["max_connections"] == 20
        assert config.redis_password is None

    def test_production_environment_complete(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test complete production environment configuration."""
        # Typical production environment
        env_vars = {
            "REDIS_HOST": "redis-cluster-prod.company.com",
            "REDIS_PORT": "6380",
            "REDIS_PASSWORD": "prod-super-secret-password-v2",
            "REDIS_DB": "1",
            "REDIS_MAX_CONNECTIONS": "100",
            "REDIS_SOCKET_CONNECT_TIMEOUT": "10",
            "REDIS_SOCKET_KEEPALIVE": "true",
            "REDIS_RETRY_ON_TIMEOUT": "true",
            "REDIS_HEALTH_CHECK_INTERVAL": "60",
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        config = RedisConfig()

        assert config.is_development is False
        assert config.redis_url == "redis://:prod-super-secret-password-v2@redis-cluster-prod.company.com:6380/1"
        assert config.connection_pool_config["max_connections"] == 100
        assert config.connection_pool_config["socket_connect_timeout"] == 10
        assert config.connection_pool_config["health_check_interval"] == 60

    def test_redis_cluster_configuration(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Redis cluster configuration scenario."""
        env_vars = {
            "REDIS_HOST": "redis-cluster-node1.internal",
            "REDIS_PORT": "7000",  # Typical cluster port
            "REDIS_PASSWORD": "cluster-auth-token",
            "REDIS_DB": "0",  # Clusters typically use db 0
            "REDIS_MAX_CONNECTIONS": "200",  # Higher for cluster
            "REDIS_SOCKET_CONNECT_TIMEOUT": "15",  # Longer for cluster
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        config = RedisConfig()

        assert config.redis_host == "redis-cluster-node1.internal"
        assert config.redis_port == 7000
        assert config.redis_db == 0
        assert config.redis_max_connections == 200
        assert config.redis_socket_connect_timeout == 15

    def test_redis_sentinel_configuration(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Redis Sentinel configuration scenario."""
        env_vars = {
            "REDIS_HOST": "redis-sentinel.service.consul",
            "REDIS_PORT": "26379",  # Sentinel port
            "REDIS_PASSWORD": "sentinel-password",
            "REDIS_DB": "0",
            "REDIS_HEALTH_CHECK_INTERVAL": "10",  # More frequent for sentinel
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        config = RedisConfig()

        assert config.redis_port == 26379
        assert config.redis_health_check_interval == 10
        assert "sentinel-password" in config.redis_url

    def test_high_performance_configuration(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test high-performance Redis configuration."""
        env_vars = {
            "REDIS_HOST": "redis-high-perf.internal",
            "REDIS_PORT": "6379",
            "REDIS_MAX_CONNECTIONS": "500",  # High connection count
            "REDIS_SOCKET_CONNECT_TIMEOUT": "2",  # Fast timeout
            "REDIS_SOCKET_KEEPALIVE": "true",
            "REDIS_RETRY_ON_TIMEOUT": "false",  # Fail fast
            "REDIS_HEALTH_CHECK_INTERVAL": "5",  # Frequent health checks
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        config = RedisConfig()

        pool_config = config.connection_pool_config
        assert pool_config["max_connections"] == 500
        assert pool_config["socket_connect_timeout"] == 2
        assert pool_config["retry_on_timeout"] is False
        assert pool_config["health_check_interval"] == 5

    def test_docker_container_configuration(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Docker container Redis configuration."""
        # Common Docker/Kubernetes scenario
        env_vars = {
            "REDIS_HOST": "redis-service",  # Kubernetes service name
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": "k8s-redis-secret",
            "REDIS_DB": "0",
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        config = RedisConfig()

        assert config.redis_host == "redis-service"
        assert config.is_development is False  # Not localhost
        assert config.redis_url == "redis://:k8s-redis-secret@redis-service:6379/0"
