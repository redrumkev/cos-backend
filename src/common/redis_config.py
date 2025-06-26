"""Redis configuration management using Pydantic Settings.

This module provides Redis configuration management with support for:
- Environment variable configuration
- REDIS_URL override support
- Password URL encoding
- Environment-specific defaults
- Proper type hints for mypy
"""

import urllib.parse
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Optional dotenv support
try:
    import os
    from pathlib import Path

    from dotenv import load_dotenv

    # Load .env file if it exists
    env_file = Path(os.getenv("ENV_FILE", ".env"))
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    # python-dotenv not installed, skip loading
    pass


class RedisConfig(BaseSettings):
    """Redis configuration settings with environment variable support.

    This class provides a comprehensive Redis configuration system that:
    - Loads settings from environment variables
    - Supports REDIS_URL override
    - Provides connection pooling configuration
    - Handles password URL encoding
    - Detects development vs production environments
    """

    model_config = SettingsConfigDict(
        env_prefix="",  # No prefix - we use full env var names
        case_sensitive=False,
        extra="ignore",
    )

    # Basic Redis connection settings
    redis_host: str = Field(default="localhost", description="Redis server hostname")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis server port")
    redis_password: str | None = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, ge=0, description="Redis database number")

    # Full Redis URL override (takes precedence over individual settings)
    redis_url_override: str | None = Field(default=None, alias="REDIS_URL", description="Complete Redis URL")

    # Connection pool settings
    redis_max_connections: int = Field(default=20, ge=1, description="Maximum connections in pool")
    redis_socket_connect_timeout: int = Field(default=5, ge=1, description="Connection timeout in seconds")
    redis_socket_keepalive: bool = Field(default=True, description="Enable socket keepalive")
    redis_retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    redis_health_check_interval: int = Field(default=30, ge=1, description="Health check interval in seconds")

    @field_validator("redis_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate Redis port is in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v

    @field_validator("redis_db")
    @classmethod
    def validate_db(cls, v: int) -> int:
        """Validate Redis database number."""
        if v < 0:
            raise ValueError(f"Database number must be >= 0, got {v}")
        return v

    @field_validator("redis_max_connections")
    @classmethod
    def validate_max_connections(cls, v: int) -> int:
        """Validate max connections is positive."""
        if v < 1:
            raise ValueError(f"Max connections must be positive, got {v}")
        return v

    @field_validator("redis_socket_connect_timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate connection timeout is positive."""
        if v < 1:
            raise ValueError(f"Timeout must be positive, got {v}")
        return v

    @field_validator("redis_health_check_interval")
    @classmethod
    def validate_health_check_interval(cls, v: int) -> int:
        """Validate health check interval is positive."""
        if v < 1:
            raise ValueError(f"Health check interval must be positive, got {v}")
        return v

    @property
    def redis_url(self) -> str:
        """Generate Redis URL from configuration.

        If REDIS_URL is set, it takes precedence over individual settings.
        Otherwise, constructs URL from host, port, password, and database.
        """
        # Use override URL if provided
        if self.redis_url_override:
            return self.redis_url_override

        # Construct URL from individual components
        if self.redis_password:
            # URL encode the password for special characters
            encoded_password = urllib.parse.quote(self.redis_password, safe="")
            auth_part = f":{encoded_password}@"
        else:
            auth_part = ""

        return f"redis://{auth_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def connection_pool_config(self) -> dict[str, Any]:
        """Get connection pool configuration dictionary."""
        return {
            "max_connections": self.redis_max_connections,
            "socket_connect_timeout": self.redis_socket_connect_timeout,
            "socket_keepalive": self.redis_socket_keepalive,
            "retry_on_timeout": self.redis_retry_on_timeout,
            "health_check_interval": self.redis_health_check_interval,
        }

    @property
    def is_development(self) -> bool:
        """Check if this is a development environment."""
        return self.redis_host in ("localhost", "127.0.0.1")

    def __str__(self) -> str:
        """Return string representation masking sensitive data."""
        # Mask password in URL for logging
        url = self.redis_url
        if self.redis_password and "@" in url:
            # Replace password with asterisks
            parts = url.split("://", 1)
            if len(parts) == 2:
                protocol, rest = parts
                if "@" in rest:
                    auth_and_host = rest.split("@", 1)
                    if len(auth_and_host) == 2:
                        auth, host_part = auth_and_host
                        if ":" in auth:
                            user, _ = auth.split(":", 1)
                            masked_url = f"{protocol}://{user}:***@{host_part}"
                        else:
                            masked_url = f"{protocol}://***@{host_part}"
                        url = masked_url

        return f"RedisConfig(host={self.redis_host}, port={self.redis_port}, db={self.redis_db}, url={url})"


@lru_cache(maxsize=1)
def get_redis_config() -> RedisConfig:
    """Get cached Redis configuration instance.

    This function uses LRU cache to ensure the same configuration
    instance is returned across the application, improving performance
    and consistency.

    Returns
    -------
        RedisConfig: Configured Redis settings instance

    """
    return RedisConfig()


async def get_redis_config_dep() -> RedisConfig:
    """FastAPI dependency for Redis configuration.

    This async function provides Redis configuration as a FastAPI dependency.
    It uses the cached get_redis_config() function internally.

    Returns
    -------
        RedisConfig: Configured Redis settings instance

    """
    return get_redis_config()
