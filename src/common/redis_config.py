"""Redis configuration module for COS.

This module provides Redis connection configuration management using Pydantic settings.
It follows the existing COS configuration patterns and supports both development and
production environments with environment variable overrides.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

# Gracefully handle optional python-dotenv dependency
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    logging.getLogger(__name__).warning("python-dotenv not installed; environment files will be ignored.")

    def load_dotenv(_path: str | os.PathLike[str] | None = None, *args: object, **kwargs: object) -> None:  # type: ignore[override]
        """Fallback no-op load_dotenv when dotenv is not available."""
        return


from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables using the same pattern as config.py
candidate = os.getenv("ENV_FILE") or str(Path(__file__).parents[2] / "infrastructure" / ".env")
if Path(candidate).exists():
    load_dotenv(candidate)


class RedisConfig(BaseSettings):
    """Redis configuration settings with environment variable support.

    Provides comprehensive Redis connection configuration following COS patterns.
    Supports both development and production environments with validation.
    """

    # Core Redis connection settings
    redis_host: str = Field(
        default="localhost", validation_alias="REDIS_HOST", description="Redis server hostname or IP address"
    )

    redis_port: int = Field(
        default=6379, ge=1, le=65535, validation_alias="REDIS_PORT", description="Redis server port number"
    )

    redis_password: str | None = Field(
        default=None, validation_alias="REDIS_PASSWORD", description="Redis server password (optional)"
    )

    redis_db: int = Field(default=0, ge=0, validation_alias="REDIS_DB", description="Redis database number")

    # Connection pool configuration
    redis_max_connections: int = Field(
        default=20,
        ge=1,
        validation_alias="REDIS_MAX_CONNECTIONS",
        description="Maximum number of connections in the pool",
    )

    redis_socket_connect_timeout: int = Field(
        default=5,
        ge=1,
        validation_alias="REDIS_SOCKET_CONNECT_TIMEOUT",
        description="Socket connection timeout in seconds",
    )

    redis_socket_keepalive: bool = Field(
        default=True, validation_alias="REDIS_SOCKET_KEEPALIVE", description="Enable socket keepalive"
    )

    redis_retry_on_timeout: bool = Field(
        default=True, validation_alias="REDIS_RETRY_ON_TIMEOUT", description="Retry operations on timeout"
    )

    redis_health_check_interval: int = Field(
        default=30, ge=1, validation_alias="REDIS_HEALTH_CHECK_INTERVAL", description="Health check interval in seconds"
    )

    model_config = SettingsConfigDict(
        env_file=None,  # dotenv loaded manually
        extra="forbid",  # Explicitly forbid extra fields for clarity
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        """Generate Redis URL from connection parameters.

        Returns
        -------
            Complete Redis URL string for connection

        """
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def connection_pool_config(self) -> dict[str, int | bool]:
        """Generate connection pool configuration dictionary.

        Returns
        -------
            Dictionary containing all connection pool settings

        """
        return {
            "max_connections": self.redis_max_connections,
            "socket_connect_timeout": self.redis_socket_connect_timeout,
            "socket_keepalive": self.redis_socket_keepalive,
            "retry_on_timeout": self.redis_retry_on_timeout,
            "health_check_interval": self.redis_health_check_interval,
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        """Determine if this is a development environment.

        Returns
        -------
            True if running in development mode (localhost), False otherwise

        """
        return self.redis_host in ("localhost", "127.0.0.1")

    def __str__(self) -> str:
        """Return string representation of Redis configuration.

        Returns
        -------
            Human-readable configuration summary

        """
        return f"RedisConfig(host={self.redis_host}, port={self.redis_port}, db={self.redis_db})"


@lru_cache
def get_redis_config() -> RedisConfig:
    """Get cached Redis configuration instance.

    Returns
    -------
        Singleton RedisConfig instance with current environment settings

    """
    return RedisConfig()


# FastAPI dependency
async def get_redis_config_dep() -> RedisConfig:
    """FastAPI dependency for Redis configuration.

    Returns
    -------
        RedisConfig instance for dependency injection

    """
    return get_redis_config()
