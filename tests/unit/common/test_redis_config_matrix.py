"""Redis configuration matrix testing for various environment setups.

This module tests Redis configuration handling across different environment
variable combinations, connection parameters, and deployment scenarios.
"""

import os
from typing import Any
from unittest.mock import patch

import pytest

from src.common.redis_config import get_redis_config


class TestRedisConfigurationMatrix:
    """Test Redis configuration with various environment variable combinations."""

    @pytest.fixture
    def clean_env(self, monkeypatch: Any) -> None:
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

    @pytest.mark.parametrize(
        "redis_host,redis_port,expected_url",
        [
            ("localhost", "6379", "redis://localhost:6379"),
            ("redis.example.com", "6380", "redis://redis.example.com:6380"),
            ("127.0.0.1", "6379", "redis://127.0.0.1:6379"),
            ("redis-cluster", "7000", "redis://redis-cluster:7000"),
        ],
    )
    async def test_host_port_combinations(
        self,
        clean_env: None,
        monkeypatch: Any,
        redis_host: str,
        redis_port: str,
        expected_url: str,
    ) -> None:
        """Test Redis configuration with different host/port combinations."""
        monkeypatch.setenv("REDIS_HOST", redis_host)
        monkeypatch.setenv("REDIS_PORT", redis_port)

        config = get_redis_config()
        assert config.redis_url == expected_url

    @pytest.mark.parametrize(
        "password,db,expected_url",
        [
            (None, None, "redis://localhost:6379"),
            ("secret123", None, "redis://:secret123@localhost:6379"),
            (None, "2", "redis://localhost:6379/2"),
            ("secret123", "5", "redis://:secret123@localhost:6379/5"),
            ("complex@pass:word", "0", "redis://:complex%40pass%3Aword@localhost:6379/0"),
        ],
    )
    async def test_auth_and_database_combinations(
        self,
        clean_env: None,
        monkeypatch: Any,
        password: str | None,
        db: str | None,
        expected_url: str,
    ) -> None:
        """Test Redis configuration with authentication and database options."""
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")

        if password:
            monkeypatch.setenv("REDIS_PASSWORD", password)
        if db:
            monkeypatch.setenv("REDIS_DB", db)

        config = get_redis_config()
        assert config.redis_url == expected_url

    @pytest.mark.parametrize(
        "full_url",
        [
            "redis://localhost:6379",
            "redis://:password@localhost:6379/1",
            "redis://user:pass@redis.example.com:6380/0",
            "rediss://secure.redis.com:6380",  # SSL
            "redis://localhost:6379?ssl_cert_reqs=none",
            "redis://cluster:7000,cluster:7001,cluster:7002",  # Cluster
        ],
    )
    async def test_full_redis_url_override(
        self,
        clean_env: None,
        monkeypatch: Any,
        full_url: str,
    ) -> None:
        """Test that REDIS_URL environment variable overrides other settings."""
        # Set individual components that should be ignored
        monkeypatch.setenv("REDIS_HOST", "should-be-ignored")
        monkeypatch.setenv("REDIS_PORT", "9999")
        monkeypatch.setenv("REDIS_PASSWORD", "ignored-password")
        monkeypatch.setenv("REDIS_DB", "9")

        # Set full URL which should take precedence
        monkeypatch.setenv("REDIS_URL", full_url)

        config = get_redis_config()
        assert config.redis_url == full_url

    @pytest.mark.parametrize(
        "env_type,expected_defaults",
        [
            (
                "development",
                {
                    "max_connections": 10,
                    "socket_connect_timeout": 5,
                    "socket_keepalive": True,
                    "retry_on_timeout": True,
                    "health_check_interval": 30,
                },
            ),
            (
                "testing",
                {
                    "max_connections": 5,  # Lower for testing
                    "socket_connect_timeout": 2,  # Faster timeout
                    "socket_keepalive": False,  # Simpler for tests
                    "retry_on_timeout": False,  # Fail fast in tests
                    "health_check_interval": 10,  # More frequent
                },
            ),
            (
                "production",
                {
                    "max_connections": 20,
                    "socket_connect_timeout": 10,
                    "socket_keepalive": True,
                    "retry_on_timeout": True,
                    "health_check_interval": 60,
                },
            ),
        ],
    )
    async def test_environment_specific_defaults(
        self,
        clean_env: None,
        monkeypatch: Any,
        env_type: str,
        expected_defaults: dict[str, Any],
    ) -> None:
        """Test that configuration defaults vary by environment type."""
        monkeypatch.setenv("ENV", env_type)

        config = get_redis_config()

        assert config.redis_max_connections == expected_defaults["max_connections"]
        assert config.redis_socket_connect_timeout == expected_defaults["socket_connect_timeout"]
        assert config.redis_socket_keepalive == expected_defaults["socket_keepalive"]
        assert config.redis_retry_on_timeout == expected_defaults["retry_on_timeout"]
        assert config.redis_health_check_interval == expected_defaults["health_check_interval"]

    @pytest.mark.parametrize(
        "max_conn,conn_timeout,keepalive,retry,health_interval",
        [
            ("50", "15", "true", "true", "120"),
            ("1", "1", "false", "false", "5"),
            ("100", "30", "1", "0", "300"),  # Test numeric boolean conversion
        ],
    )
    async def test_custom_connection_parameters(
        self,
        clean_env: None,
        monkeypatch: Any,
        max_conn: str,
        conn_timeout: str,
        keepalive: str,
        retry: str,
        health_interval: str,
    ) -> None:
        """Test custom Redis connection parameter configurations."""
        monkeypatch.setenv("REDIS_MAX_CONNECTIONS", max_conn)
        monkeypatch.setenv("REDIS_SOCKET_CONNECT_TIMEOUT", conn_timeout)
        monkeypatch.setenv("REDIS_SOCKET_KEEPALIVE", keepalive)
        monkeypatch.setenv("REDIS_RETRY_ON_TIMEOUT", retry)
        monkeypatch.setenv("REDIS_HEALTH_CHECK_INTERVAL", health_interval)

        config = get_redis_config()

        assert config.redis_max_connections == int(max_conn)
        assert config.redis_socket_connect_timeout == int(conn_timeout)

        # Test boolean conversion
        expected_keepalive = keepalive.lower() in ("true", "1", "yes", "on")
        expected_retry = retry.lower() in ("true", "1", "yes", "on")

        assert config.redis_socket_keepalive == expected_keepalive
        assert config.redis_retry_on_timeout == expected_retry
        assert config.redis_health_check_interval == int(health_interval)

    async def test_invalid_configuration_handling(
        self,
        clean_env: None,
        monkeypatch: Any,
    ) -> None:
        """Test handling of invalid configuration values."""
        # Invalid port number
        monkeypatch.setenv("REDIS_PORT", "invalid")

        with pytest.raises(ValueError, match="invalid literal for int()"):
            get_redis_config()

        # Reset and test negative values
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_MAX_CONNECTIONS", "-1")

        with pytest.raises(ValueError, match="must be positive"):
            get_redis_config()

    async def test_configuration_caching_and_reload(
        self,
        clean_env: None,
        monkeypatch: Any,
    ) -> None:
        """Test that configuration caching and reloading works correctly."""
        # Set initial configuration
        monkeypatch.setenv("REDIS_HOST", "initial-host")
        monkeypatch.setenv("REDIS_PORT", "6379")

        config1 = get_redis_config()
        assert "initial-host" in config1.redis_url

        # Change environment (simulating runtime config change)
        monkeypatch.setenv("REDIS_HOST", "updated-host")

        # Should get cached version first
        config2 = get_redis_config()
        assert config2 is config1  # Same object reference

        # Force reload by clearing cache
        with patch("src.common.redis_config._config_cache", None):
            config3 = get_redis_config()
            assert "updated-host" in config3.redis_url

    @pytest.mark.parametrize(
        "missing_vars,expected_fallbacks",
        [
            (["REDIS_HOST"], {"host": "localhost"}),
            (["REDIS_PORT"], {"port": 6379}),
            (["REDIS_HOST", "REDIS_PORT"], {"host": "localhost", "port": 6379}),
            (["REDIS_PASSWORD"], {"password": None}),
            (["REDIS_DB"], {"db": 0}),
        ],
    )
    async def test_fallback_behavior(
        self,
        clean_env: None,
        monkeypatch: Any,
        missing_vars: list[str],
        expected_fallbacks: dict[str, Any],
    ) -> None:
        """Test fallback behavior when environment variables are missing."""
        # Set minimal required vars
        base_vars = {
            "REDIS_HOST": "test-host",
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": "test-pass",
            "REDIS_DB": "1",
        }

        # Remove specific variables to test fallbacks
        for var in base_vars:
            if var not in missing_vars:
                monkeypatch.setenv(var, base_vars[var])

        config = get_redis_config()

        # Verify fallbacks are applied
        if "host" in expected_fallbacks:
            assert expected_fallbacks["host"] in config.redis_url
        if "port" in expected_fallbacks:
            assert str(expected_fallbacks["port"]) in config.redis_url
        if expected_fallbacks.get("password") is None:
            assert "@" not in config.redis_url or ":@" in config.redis_url
        if "db" in expected_fallbacks and expected_fallbacks["db"] == 0:
            assert config.redis_url.endswith(":6379") or not config.redis_url.endswith("/1")


class TestRedisConfigurationInDockerEnvironments:
    """Test Redis configuration for containerized deployment scenarios."""

    async def test_docker_compose_service_discovery(
        self,
        clean_env: None,
        monkeypatch: Any,
    ) -> None:
        """Test Redis configuration using Docker Compose service names."""
        # Simulate Docker Compose environment
        monkeypatch.setenv("REDIS_HOST", "redis")  # Docker service name
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("ENV", "development")

        config = get_redis_config()
        assert config.redis_url == "redis://redis:6379"

        # Should use development defaults for connection pooling
        assert config.redis_max_connections == 10

    async def test_kubernetes_environment_variables(
        self,
        clean_env: None,
        monkeypatch: Any,
    ) -> None:
        """Test Redis configuration with Kubernetes-style environment variables."""
        # Simulate Kubernetes Redis service
        monkeypatch.setenv("REDIS_SERVICE_HOST", "10.96.0.100")
        monkeypatch.setenv("REDIS_SERVICE_PORT", "6379")

        # Custom mapping for K8s environment
        redis_host = os.getenv("REDIS_SERVICE_HOST", "localhost")
        redis_port = os.getenv("REDIS_SERVICE_PORT", "6379")

        monkeypatch.setenv("REDIS_HOST", redis_host)
        monkeypatch.setenv("REDIS_PORT", redis_port)
        monkeypatch.setenv("ENV", "production")

        config = get_redis_config()
        assert config.redis_url == "redis://10.96.0.100:6379"
        assert config.redis_max_connections == 20  # Production defaults

    async def test_cloud_provider_configurations(
        self,
        clean_env: None,
        monkeypatch: Any,
    ) -> None:
        """Test Redis configuration for various cloud providers."""
        cloud_configs = [
            # AWS ElastiCache
            {
                "url": "redis://my-cluster.abc123.cache.amazonaws.com:6379",
                "env": "production",
            },
            # Google Cloud Memorystore
            {
                "url": "redis://10.0.0.3:6379",
                "env": "production",
            },
            # Azure Cache for Redis
            {
                "url": "rediss://:password@my-redis.redis.cache.windows.net:6380",
                "env": "production",
            },
            # DigitalOcean Managed Redis
            {
                "url": "rediss://default:password@redis-cluster-123.db.ondigitalocean.com:25061",
                "env": "production",
            },
        ]

        for cloud_config in cloud_configs:
            # Clear previous config
            with patch("src.common.redis_config._config_cache", None):
                monkeypatch.setenv("REDIS_URL", cloud_config["url"])
                monkeypatch.setenv("ENV", cloud_config["env"])

                config = get_redis_config()
                assert config.redis_url == cloud_config["url"]

                # Should use production settings for cloud environments
                assert config.redis_max_connections >= 20
                assert config.redis_socket_connect_timeout >= 5
                assert config.redis_socket_keepalive is True


class TestRedisConfigurationSecurity:
    """Test Redis configuration security and credential handling."""

    async def test_password_url_encoding(
        self,
        clean_env: None,
        monkeypatch: Any,
    ) -> None:
        """Test that passwords with special characters are properly URL encoded."""
        special_passwords = [
            "simple123",
            "pass@word",
            "user:pass",
            "redis://fake",
            "p@ss:w0rd!",
            "пароль",  # Unicode
            "密码",  # Chinese
        ]

        for password in special_passwords:
            # Clear previous config
            with patch("src.common.redis_config._config_cache", None):
                monkeypatch.setenv("REDIS_HOST", "localhost")
                monkeypatch.setenv("REDIS_PORT", "6379")
                monkeypatch.setenv("REDIS_PASSWORD", password)

                config = get_redis_config()

                # URL should contain encoded password
                assert config.redis_url.startswith("redis://:")
                assert "@localhost:6379" in config.redis_url

                # Verify we can extract the password from URL
                import urllib.parse

                parsed = urllib.parse.urlparse(config.redis_url)
                decoded_password = urllib.parse.unquote(parsed.password or "")
                assert decoded_password == password

    async def test_credential_masking_in_logs(
        self,
        clean_env: None,
        monkeypatch: Any,
        caplog: Any,
    ) -> None:
        """Test that credentials are masked in log output."""
        monkeypatch.setenv("REDIS_URL", "redis://:secret123@localhost:6379")

        config = get_redis_config()

        # Convert config to string (simulating logging)
        config_str = str(config)

        # Should not contain the actual password
        assert "secret123" not in config_str
        assert "***" in config_str or "MASKED" in config_str.upper()

    async def test_configuration_validation(
        self,
        clean_env: None,
        monkeypatch: Any,
    ) -> None:
        """Test validation of Redis configuration parameters."""
        invalid_configs = [
            # Invalid port range
            {"REDIS_PORT": "70000"},
            {"REDIS_PORT": "0"},
            # Invalid connection limits
            {"REDIS_MAX_CONNECTIONS": "0"},
            {"REDIS_MAX_CONNECTIONS": "10000"},
            # Invalid timeout values
            {"REDIS_SOCKET_CONNECT_TIMEOUT": "0"},
            {"REDIS_SOCKET_CONNECT_TIMEOUT": "3600"},
            # Invalid health check interval
            {"REDIS_HEALTH_CHECK_INTERVAL": "0"},
        ]

        for invalid_config in invalid_configs:
            # Clear previous config
            with patch("src.common.redis_config._config_cache", None):
                # Set base valid config
                monkeypatch.setenv("REDIS_HOST", "localhost")
                monkeypatch.setenv("REDIS_PORT", "6379")

                # Apply invalid setting
                for key, value in invalid_config.items():
                    monkeypatch.setenv(key, value)

                # Should raise validation error
                with pytest.raises((ValueError, AssertionError)):
                    get_redis_config()

                # Clean up invalid setting
                for key in invalid_config:
                    monkeypatch.delenv(key, raising=False)
