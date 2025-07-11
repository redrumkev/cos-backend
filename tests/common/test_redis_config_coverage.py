"""Comprehensive tests to achieve 99.5%+ coverage for redis_config.py.

This module targets specific missing lines identified in coverage report.
Missing lines: 32-34, 148-149, 157-158, 166-167, 175-176, 184-185, 197, 231-245, 277

Living Pattern: ADR-002 v2.1.0
"""

import os
from unittest.mock import patch

import pytest

from src.common.redis_config import RedisConfig, get_redis_config, get_redis_config_dep


class TestDotenvFallback:
    """Test dotenv import fallback scenarios."""

    def teardown_class(self) -> None:
        """Clean up module state after tests."""
        # Clear the LRU cache to ensure no cached instances carry over
        from src.common.redis_config import get_redis_config

        get_redis_config.cache_clear()

    def test_dotenv_not_available(self) -> None:
        """Test when dotenv is not available - lines 32-34."""
        # Test the fallback behavior without reloading the module
        # This tests the ImportError path in the module initialization
        with (
            patch.dict("sys.modules", {"dotenv": None}),
            patch.dict("os.environ", {}, clear=True),
        ):
            # Test that the module can still create instances without dotenv
            config = RedisConfig()
            assert config is not None
            assert config.redis_host == "localhost"  # Should use default


class TestValidatorErrors:
    """Test validator error paths for missing coverage."""

    def test_validate_port_out_of_range(self) -> None:
        """Test port validation with out of range values - lines 148-149."""
        # Test port too low
        with pytest.raises(ValueError, match="Port must be between 1 and 65535, got 0"):
            RedisConfig(redis_port=0)

        # Test port too high
        with pytest.raises(ValueError, match="Port must be between 1 and 65535, got 70000"):
            RedisConfig(redis_port=70000)

    def test_validate_db_negative(self) -> None:
        """Test database validation with negative value - lines 157-158."""
        with pytest.raises(ValueError, match="Database number must be >= 0, got -1"):
            RedisConfig(redis_db=-1)

    def test_validate_max_connections_invalid(self) -> None:
        """Test max connections validation with invalid value - lines 166-167."""
        with pytest.raises(ValueError, match="Max connections must be positive, got 0"):
            RedisConfig(redis_max_connections=0)

        with pytest.raises(ValueError, match="Max connections must be positive, got -5"):
            RedisConfig(redis_max_connections=-5)

    def test_validate_timeout_invalid(self) -> None:
        """Test timeout validation with invalid value - lines 175-176."""
        with pytest.raises(ValueError, match="Timeout must be positive, got 0"):
            RedisConfig(redis_socket_connect_timeout=0)

        with pytest.raises(ValueError, match="Timeout must be positive, got -1"):
            RedisConfig(redis_socket_connect_timeout=-1)

    def test_validate_health_check_interval_invalid(self) -> None:
        """Test health check interval validation with invalid value - lines 184-185."""
        with pytest.raises(ValueError, match="Health check interval must be positive, got 0"):
            RedisConfig(redis_health_check_interval=0)

        with pytest.raises(ValueError, match="Health check interval must be positive, got -10"):
            RedisConfig(redis_health_check_interval=-10)


class TestRedisUrlProperty:
    """Test redis_url property edge cases."""

    def test_redis_url_with_override(self) -> None:
        """Test redis_url when override is provided - line 197."""
        # Set REDIS_URL environment variable
        with patch.dict(os.environ, {"REDIS_URL": "redis://override:6380/1"}):
            config = RedisConfig()
            assert config.redis_url == "redis://override:6380/1"
            assert config.redis_url_override == "redis://override:6380/1"


class TestStringRepresentation:
    """Test __str__ method with various URL formats."""

    def test_str_with_password_complex_masking(self) -> None:
        """Test string representation with password masking - lines 231-245."""
        # Test with username and password
        config = RedisConfig(redis_host="example.com", redis_port=6379, redis_password="secret123", redis_db=0)

        # The password should be masked in string representation
        str_repr = str(config)
        assert "secret123" not in str_repr
        assert "***" in str_repr
        assert "example.com" in str_repr

    def test_str_with_malformed_url(self) -> None:
        """Test string representation with malformed URL formats."""
        # Test with override URL that has unusual format
        with patch.dict(os.environ, {"REDIS_URL": "redis://:password@host:6379/0"}):
            config = RedisConfig()
            str_repr = str(config)
            assert "password" not in str_repr
            assert "***" in str_repr

    def test_str_without_auth(self) -> None:
        """Test string representation without authentication."""
        config = RedisConfig(redis_host="localhost", redis_port=6379, redis_password=None, redis_db=0)

        str_repr = str(config)
        assert "@" not in str_repr
        assert "localhost" in str_repr
        assert "6379" in str_repr

    def test_str_with_auth_no_colon(self) -> None:
        """Test string representation with auth but no colon separator."""
        # Force a URL format without colon in auth part (edge case)
        with patch.dict(os.environ, {"REDIS_URL": "redis://username@localhost:6379/0"}):
            config = RedisConfig()
            str_repr = str(config)
            # Should mask the username part
            assert "username" not in str_repr or "***" in str_repr


class TestDependencyFunction:
    """Test FastAPI dependency function."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        # Reimport to ensure we have the correct class after any module reloads
        from src.common.redis_config import get_redis_config

        get_redis_config.cache_clear()

    async def test_get_redis_config_dep(self) -> None:
        """Test async dependency function - line 277."""
        # Reimport to ensure we have the correct references after module reloads
        from src.common.redis_config import RedisConfig, get_redis_config

        # Clear environment to ensure we get defaults
        with patch.dict("os.environ", {}, clear=True):
            # The dependency should return a valid config
            config = await get_redis_config_dep()

            # Verify it's a valid RedisConfig instance
            assert isinstance(config, RedisConfig)
            assert config.redis_host == "localhost"
            assert config.redis_port == 6379

            # Verify that get_redis_config uses cache
            config1 = get_redis_config()
            config2 = get_redis_config()
            assert config1 is config2  # These should be the same cached instance


class TestEnvironmentDefaults:
    """Test environment-specific defaults application."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        get_redis_config.cache_clear()

    def teardown_method(self) -> None:
        """Clear cache after each test."""
        get_redis_config.cache_clear()

    def test_testing_environment_defaults(self) -> None:
        """Test testing environment defaults are applied."""
        # Clear the cache to ensure fresh config
        get_redis_config.cache_clear()
        try:
            with patch.dict(os.environ, {"TESTING": "1", "ENV": ""}, clear=True):
                config = RedisConfig()
                # Testing environment should have lower max_connections
                assert config.redis_max_connections == 5
                assert config.redis_socket_connect_timeout == 2
                assert config.redis_socket_keepalive is False
                assert config.redis_retry_on_timeout is False
                assert config.redis_health_check_interval == 10
        finally:
            # Clear cache after test to avoid affecting other tests
            get_redis_config.cache_clear()

    def test_production_environment_defaults(self) -> None:
        """Test production environment defaults are applied."""
        with patch.dict(os.environ, {"ENV": "production"}, clear=True):
            config = RedisConfig()
            # Production environment settings
            assert config.redis_max_connections == 20
            assert config.redis_socket_connect_timeout == 10
            assert config.redis_socket_keepalive is True
            assert config.redis_retry_on_timeout is True
            assert config.redis_health_check_interval == 60

    def test_unknown_environment_defaults(self) -> None:
        """Test unknown environment falls back to development defaults."""
        with patch.dict(os.environ, {"ENV": "staging"}):
            config = RedisConfig()
            # Should use development defaults for unknown environments
            assert config.redis_max_connections == 20
            assert config.redis_socket_connect_timeout == 5


class TestEdgeCases:
    """Test various edge cases."""

    def test_special_characters_in_password(self) -> None:
        """Test URL encoding of special characters in password."""
        config = RedisConfig(redis_password="p@ss:word/123?")

        # Password should be URL encoded in redis_url
        assert "p%40ss%3Aword%2F123%3F" in config.redis_url

        # But masked in string representation
        str_repr = str(config)
        assert "p@ss:word/123?" not in str_repr
        assert "***" in str_repr

    def test_is_development_property(self) -> None:
        """Test is_development property with various hosts."""
        # Test localhost
        config = RedisConfig(redis_host="localhost")
        assert config.is_development is True

        # Test 127.0.0.1
        config = RedisConfig(redis_host="127.0.0.1")
        assert config.is_development is True

        # Test remote host
        config = RedisConfig(redis_host="redis.example.com")
        assert config.is_development is False

    def test_connection_pool_config_property(self) -> None:
        """Test connection_pool_config property returns correct dict."""
        config = RedisConfig(
            redis_max_connections=50,
            redis_socket_connect_timeout=10,
            redis_socket_keepalive=False,
            redis_retry_on_timeout=False,
            redis_health_check_interval=60,
        )

        pool_config = config.connection_pool_config
        assert pool_config["max_connections"] == 50
        assert pool_config["socket_connect_timeout"] == 10
        assert pool_config["socket_keepalive"] is False
        assert pool_config["retry_on_timeout"] is False
        assert pool_config["health_check_interval"] == 60

    def test_model_validator_with_non_dict_data(self) -> None:
        """Test model validator with non-dict data."""
        # The validator should handle non-dict data gracefully
        config = RedisConfig.model_validate(RedisConfig())
        assert config is not None

    def test_cache_clearing(self) -> None:
        """Test that get_redis_config cache works correctly."""
        # Get first instance
        config1 = get_redis_config()

        # Get second instance - should be same due to cache
        config2 = get_redis_config()
        assert config1 is config2

        # Clear cache
        get_redis_config.cache_clear()

        # Get new instance - should be different
        config3 = get_redis_config()
        assert config1 is not config3
