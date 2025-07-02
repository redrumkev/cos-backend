"""Shared fixtures for common module unit tests."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio

# Error messages
SIMULATED_FAILURE_MSG = "Simulated connection failure"
MAX_FAILURES = 3


# Removed session-scoped event loop to prevent conflicts
# Using pytest-asyncio's default function-scoped event loop instead


@pytest_asyncio.fixture
async def fake_redis() -> AsyncGenerator[Any, None]:
    """Async fakeredis instance with proper cleanup.

    Each test gets its own isolated FakeRedis instance to prevent state leakage.
    """
    try:
        from fakeredis import FakeAsyncRedis
    except ImportError:
        pytest.skip("fakeredis not available")

    # Create a fresh isolated instance for each test
    redis_client = FakeAsyncRedis(
        decode_responses=False,
        socket_keepalive=True,
        retry_on_timeout=True,
    )

    try:
        yield redis_client
    finally:
        # Ensure complete cleanup
        await redis_client.flushall()
        await redis_client.aclose()


@pytest_asyncio.fixture
async def flaky_redis(fake_redis: Any) -> AsyncGenerator[Any, None]:
    """Redis client that simulates failures."""
    failure_count = 0

    original_publish = fake_redis.publish
    original_ping = fake_redis.ping

    async def failing_publish(*args: Any, **kwargs: Any) -> Any:
        nonlocal failure_count
        if failure_count < MAX_FAILURES:
            failure_count += 1
            from redis.exceptions import RedisError

            error_msg = f"Simulated failure {failure_count}"
            raise RedisError(error_msg)
        return await original_publish(*args, **kwargs)

    async def failing_ping(*args: Any, **kwargs: Any) -> Any:
        nonlocal failure_count
        if failure_count < MAX_FAILURES:
            failure_count += 1
            from redis.exceptions import ConnectionError as RedisConnectionError

            raise RedisConnectionError(SIMULATED_FAILURE_MSG)
        return await original_ping(*args, **kwargs)

    fake_redis.publish = failing_publish
    fake_redis.ping = failing_ping

    try:
        yield fake_redis
    finally:
        fake_redis.publish = original_publish
        fake_redis.ping = original_ping


@pytest.fixture
def mock_redis_config() -> Any:
    """Mock Redis configuration for testing."""
    return type(
        "MockConfig",
        (),
        {
            "redis_url": "redis://localhost:6379",
            "redis_max_connections": 10,
            "redis_socket_connect_timeout": 5,
            "redis_socket_keepalive": True,
            "redis_retry_on_timeout": True,
            "redis_health_check_interval": 30,
        },
    )()


@pytest.fixture
def circuit_breaker_config() -> dict[str, Any]:
    """Return standard circuit breaker configuration for testing."""
    return {
        "failure_threshold": 3,
        "recovery_timeout": 1.0,
        "success_threshold": 2,
        "timeout": 0.5,
    }
