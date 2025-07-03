"""Mock service utilities for testing failure scenarios without Docker operations."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import redis.exceptions
from sqlalchemy.exc import DisconnectionError, OperationalError


@asynccontextmanager
async def mock_service_interruption(
    service_name: str, interruption_type: str = "connection_error", delay: float | None = None
) -> AsyncGenerator[None, None]:
    """Mock service interruption without actual Docker operations.

    This replaces the Docker-based service_interruption to avoid manual intervention.
    It simulates the same failure conditions by mocking client libraries.

    Args:
    ----
        service_name: Name of service to mock interruption for (e.g., "cos_redis")
        interruption_type: Type of failure to simulate:
            - "connection_error": Immediate connection failures
            - "timeout": Operations timeout after delay
            - "pubsub_failure": Pub/sub specific failures
        delay: Optional delay before failure (for timeout simulation)

    """
    if service_name == "cos_redis":
        async with _mock_redis_interruption(interruption_type, delay):
            yield
    elif service_name == "cos_postgres_dev":
        async with _mock_postgres_interruption(interruption_type, delay):
            yield
    else:
        # For other services, just yield without mocking
        yield


@asynccontextmanager
async def _mock_redis_interruption(interruption_type: str, delay: float | None) -> AsyncGenerator[None, None]:
    """Mock Redis failures without pausing containers."""
    if interruption_type == "connection_error":
        # Mock connection failures
        # Create connection error side effect
        conn_error = redis.exceptions.ConnectionError("Mocked connection failure")

        # Mock all Redis client methods
        with (
            patch("redis.asyncio.Redis.ping", side_effect=conn_error),
            patch("redis.asyncio.Redis.get", side_effect=conn_error),
            patch("redis.asyncio.Redis.set", side_effect=conn_error),
            patch("redis.asyncio.Redis.publish", side_effect=conn_error),
            # Mock pubsub instance methods
            patch("redis.asyncio.client.PubSub.get_message", side_effect=conn_error),
            patch("redis.asyncio.client.PubSub.subscribe", side_effect=conn_error),
            patch("redis.asyncio.client.PubSub.unsubscribe", side_effect=conn_error),
        ):
            # Also mock the COS pubsub client
            mock_pubsub = AsyncMock()
            mock_pubsub.publish.side_effect = conn_error
            mock_pubsub.health_check.side_effect = conn_error

            with patch("src.common.pubsub.get_pubsub", return_value=mock_pubsub):
                yield

    elif interruption_type == "timeout":
        # Mock timeout failures
        async def timeout_side_effect(*args: Any, **kwargs: Any) -> None:
            if delay:
                await asyncio.sleep(delay)
            raise redis.exceptions.TimeoutError("Mocked timeout")

        with (
            patch("redis.asyncio.Redis.ping", side_effect=timeout_side_effect),
            patch("redis.asyncio.Redis.get", side_effect=timeout_side_effect),
            patch("redis.asyncio.Redis.set", side_effect=timeout_side_effect),
            patch("redis.asyncio.Redis.publish", side_effect=timeout_side_effect),
        ):
            mock_pubsub = AsyncMock()
            mock_pubsub.publish.side_effect = timeout_side_effect
            mock_pubsub.health_check.side_effect = timeout_side_effect

            with patch("src.common.pubsub.get_pubsub", return_value=mock_pubsub):
                yield

    elif interruption_type == "pubsub_failure":
        # Mock pub/sub specific failures
        mock_pubsub = AsyncMock()
        mock_pubsub.publish.side_effect = redis.exceptions.ConnectionError("Pub/sub channel disconnected")
        mock_pubsub.subscribe.side_effect = redis.exceptions.ConnectionError("Cannot subscribe")
        mock_pubsub.health_check.return_value = MagicMock(is_healthy=False, latency_ms=None)

        with (
            patch("src.common.pubsub.get_pubsub", return_value=mock_pubsub),
            # Also patch direct Redis pubsub
            patch("redis.asyncio.Redis.pubsub") as mock_redis_pubsub,
        ):
            mock_redis_pubsub.return_value.subscribe.side_effect = redis.exceptions.ConnectionError("Cannot subscribe")
            yield
    else:
        # No mocking for unknown types
        yield


@asynccontextmanager
async def _mock_postgres_interruption(interruption_type: str, delay: float | None) -> AsyncGenerator[None, None]:
    """Mock PostgreSQL failures without stopping containers."""
    if interruption_type == "connection_error":
        # Mock database connection failures
        # Create a base exception for the OperationalError
        base_exc = Exception("Connection refused")
        with (
            patch(
                "sqlalchemy.ext.asyncio.AsyncSession.execute",
                side_effect=OperationalError("Mocked DB connection failure", None, base_exc),
            ),
            patch(
                "sqlalchemy.ext.asyncio.AsyncSession.commit", side_effect=DisconnectionError("Database disconnected")
            ),
            patch(
                "sqlalchemy.ext.asyncio.AsyncSession.rollback",
                side_effect=DisconnectionError("Database disconnected"),
            ),
        ):
            yield
    else:
        # No mocking for unknown types
        yield


# Circuit breaker state mocking utilities
def mock_circuit_breaker_state(state: str = "open") -> MagicMock:
    """Create a mock circuit breaker in the specified state."""
    mock_breaker = MagicMock()
    mock_breaker.state = state
    mock_breaker.is_closed = state == "closed"
    mock_breaker.is_open = state == "open"
    mock_breaker.is_half_open = state == "half_open"
    mock_breaker.failure_count = 5 if state == "open" else 0
    mock_breaker.last_failure = asyncio.get_event_loop().time() if state == "open" else None
    return mock_breaker
