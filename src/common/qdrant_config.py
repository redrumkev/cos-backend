"""Qdrant vector database configuration with graceful fallbacks.

This module provides configuration and connection management for Qdrant,
which will become a required service in the next sprint. Currently operates
with graceful fallbacks to avoid blocking development.

TODO: Remove optional fallbacks when Qdrant becomes required (Sprint 3)
"""

import logging
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import exceptions as qdrant_exceptions

from src.common.logger import log_event

logger = logging.getLogger(__name__)


class QdrantSettings(BaseSettings):
    """Qdrant configuration settings."""

    QDRANT_HOST: str = Field(default="localhost", description="Qdrant host")
    QDRANT_PORT: int = Field(default=6333, description="Qdrant REST API port")
    QDRANT_API_KEY: str | None = Field(default=None, description="Optional API key for production")
    QDRANT_GRPC_PORT: int = Field(default=6334, description="Qdrant gRPC port")
    QDRANT_HTTPS: bool = Field(default=False, description="Use HTTPS for connection")
    QDRANT_TIMEOUT: int = Field(default=60, description="Connection timeout in seconds")

    class Config:
        env_file = ".env"
        case_sensitive = True


class QdrantConfig:
    """Qdrant configuration and connection management with graceful fallbacks."""

    def __init__(self) -> None:
        """Initialize Qdrant configuration."""
        self.settings = QdrantSettings()
        self._client: AsyncQdrantClient | None = None
        self._available = False
        self._availability_checked = False

    async def get_client(self) -> AsyncQdrantClient | None:
        """Get Qdrant client with lazy initialization and availability check.

        Returns
        -------
            AsyncQdrantClient if available, None otherwise

        """
        if not self._availability_checked:
            await self._check_availability()

        if not self._available:
            return None

        if self._client is None:
            self._client = AsyncQdrantClient(
                host=self.settings.QDRANT_HOST,
                port=self.settings.QDRANT_PORT,
                api_key=self.settings.QDRANT_API_KEY,
                https=self.settings.QDRANT_HTTPS,
                timeout=self.settings.QDRANT_TIMEOUT,
            )

        return self._client

    async def _check_availability(self) -> None:
        """Check if Qdrant service is available."""
        self._availability_checked = True

        try:
            # Create temporary client for health check
            temp_client = AsyncQdrantClient(
                host=self.settings.QDRANT_HOST,
                port=self.settings.QDRANT_PORT,
                api_key=self.settings.QDRANT_API_KEY,
                https=self.settings.QDRANT_HTTPS,
                timeout=5,  # Short timeout for health check
            )

            # Try to get info as health check
            await temp_client.info()
            self._available = True

            log_event(
                source="qdrant_config",
                data={"status": "available", "host": self.settings.QDRANT_HOST, "port": self.settings.QDRANT_PORT},
                tags=["qdrant", "health", "available"],
                memo="Qdrant service is available",
            )

        except (qdrant_exceptions.UnexpectedResponse, qdrant_exceptions.ResponseHandlingException, OSError) as e:
            self._available = False

            log_event(
                source="qdrant_config",
                data={
                    "status": "unavailable",
                    "host": self.settings.QDRANT_HOST,
                    "port": self.settings.QDRANT_PORT,
                    "error": str(e),
                },
                tags=["qdrant", "health", "unavailable", "warning"],
                memo="Qdrant service is not available - falling back gracefully",
            )
        finally:
            # Close temporary client
            if "temp_client" in locals():
                await temp_client.close()

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on Qdrant connection.

        Returns
        -------
            Health status dictionary

        """
        if not self._availability_checked:
            await self._check_availability()

        if not self._available:
            return {
                "service": "qdrant",
                "status": "unavailable",
                "message": "Qdrant service not available - using fallback mode",
                "host": self.settings.QDRANT_HOST,
                "port": self.settings.QDRANT_PORT,
            }

        try:
            client = await self.get_client()
            if client:
                info = await client.info()
                return {
                    "service": "qdrant",
                    "status": "healthy",
                    "version": info.version if hasattr(info, "version") else "unknown",
                    "host": self.settings.QDRANT_HOST,
                    "port": self.settings.QDRANT_PORT,
                }
            else:
                return {
                    "service": "qdrant",
                    "status": "unavailable",
                    "message": "Failed to create client",
                }
        except Exception as e:
            return {
                "service": "qdrant",
                "status": "unhealthy",
                "error": str(e),
                "host": self.settings.QDRANT_HOST,
                "port": self.settings.QDRANT_PORT,
            }

    async def close(self) -> None:
        """Close Qdrant client connection."""
        if self._client:
            await self._client.close()
            self._client = None

    def is_available(self) -> bool:
        """Check if Qdrant is available without async call.

        Returns
        -------
            True if available, False otherwise

        """
        return self._available


# Global instance for easy access
_qdrant_config: QdrantConfig | None = None


def get_qdrant_config() -> QdrantConfig:
    """Get global Qdrant configuration instance.

    Returns
    -------
        QdrantConfig instance

    """
    global _qdrant_config
    if _qdrant_config is None:
        _qdrant_config = QdrantConfig()
    return _qdrant_config
