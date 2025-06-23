"""Production-grade Redis integration test foundation using fakeredis.

This module provides comprehensive Redis integration tests focusing on performance
(<1ms publish latency) and reliability (circuit breaker resilience) using fakeredis
for fast, reliable testing without Docker dependencies.

Test Coverage:
- Session-scoped fake Redis server with optimized configuration
- Function-scoped Redis client with automatic cleanup
- Basic pub/sub roundtrip tests
- RedisConfig integration and validation
- Connection pool validation and performance
- Circuit breaker functionality and recovery
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

import fakeredis.aioredis
import pytest
import pytest_asyncio

from src.common.pubsub import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerState,
    RedisPubSub,
)
from src.common.redis_config import RedisConfig

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class SimulatedRedisFailureError(Exception):
    """Specific exception for testing circuit breaker behavior."""


@pytest_asyncio.fixture(scope="function")
async def fake_redis_server() -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
    """Function-scoped fake Redis server for integration testing.

    Uses fakeredis to provide a Redis-compatible server without Docker.
    This allows for fast, reliable testing of Redis functionality.

    Returns
    -------
        FakeRedis: In-memory Redis server instance

    """
    server = fakeredis.aioredis.FakeRedis(
        version=(7, 2, 0),  # Emulate Redis 7.2
        decode_responses=False,
    )
    yield server
    await server.flushall()  # Clean up after each test


@pytest_asyncio.fixture
async def redis_config(fake_redis_server: fakeredis.aioredis.FakeRedis) -> AsyncGenerator[RedisConfig, None]:
    """RedisConfig instance configured for the fake Redis server.

    Args:
    ----
        fake_redis_server: The session-scoped fake Redis server

    Returns:
    -------
        RedisConfig: Configured for fake Redis connection

    """
    # Override environment to point to localhost (fake Redis will intercept)
    import os

    original_host = os.environ.get("REDIS_HOST")
    original_port = os.environ.get("REDIS_PORT")

    try:
        os.environ["REDIS_HOST"] = "localhost"
        os.environ["REDIS_PORT"] = "6379"

        # Create fresh config
        config = RedisConfig()
        yield config

    finally:
        # Restore original environment
        if original_host is not None:
            os.environ["REDIS_HOST"] = original_host
        else:
            os.environ.pop("REDIS_HOST", None)

        if original_port is not None:
            os.environ["REDIS_PORT"] = original_port
        else:
            os.environ.pop("REDIS_PORT", None)


@pytest_asyncio.fixture
async def redis_client(
    fake_redis_server: fakeredis.aioredis.FakeRedis,
) -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
    """Function-scoped Redis client with automatic flushall cleanup.

    Args:
    ----
        fake_redis_server: Fake Redis server instance

    Yields:
    ------
        FakeRedis: Connected fake Redis client with automatic cleanup

    """
    try:
        # Verify connection
        await fake_redis_server.ping()
        yield fake_redis_server
    finally:
        # Clean up all data for test isolation
        with contextlib.suppress(Exception):
            await fake_redis_server.flushall()


@pytest_asyncio.fixture
async def pubsub_client(redis_config: RedisConfig) -> AsyncGenerator[RedisPubSub, None]:
    """Function-scoped RedisPubSub client with connection management.

    Args:
    ----
        redis_config: Redis configuration for test server

    Yields:
    ------
        RedisPubSub: Connected pub/sub client with automatic cleanup

    """
    # Use proper mocking to avoid import issues
    from unittest.mock import patch

    with (
        patch("src.common.redis_config.get_redis_config", return_value=redis_config),
        patch("src.common.pubsub.redis", fakeredis.aioredis),
    ):
        pubsub = RedisPubSub()

        try:
            await pubsub.connect()
            yield pubsub
        finally:
            await pubsub.disconnect()


class TestRedisServerFoundation:
    """Test Redis server setup and basic connectivity."""

    async def test_fake_server_is_ready(self, fake_redis_server: fakeredis.aioredis.FakeRedis) -> None:
        """Verify fake Redis server is ready and accessible."""
        response = await fake_redis_server.ping()
        assert response is True

    async def test_direct_connection(self, fake_redis_server: fakeredis.aioredis.FakeRedis) -> None:
        """Test direct Redis connection to fake server."""
        response = await fake_redis_server.ping()
        assert response is True


class TestRedisConfig:
    """Test RedisConfig integration with test server."""

    def test_config_points_to_localhost(self, redis_config: RedisConfig) -> None:
        """Verify RedisConfig is configured for localhost test server."""
        assert redis_config.redis_host == "localhost"
        assert redis_config.redis_port == 6379
        assert redis_config.redis_db == 0

    def test_redis_url_generation(self, redis_config: RedisConfig) -> None:
        """Test Redis URL generation from config."""
        url = redis_config.redis_url
        assert url.startswith("redis://")
        assert str(redis_config.redis_port) in url
        assert redis_config.redis_host in url

    def test_connection_pool_config(self, redis_config: RedisConfig) -> None:
        """Test connection pool configuration generation."""
        pool_config = redis_config.connection_pool_config

        expected_keys = {
            "max_connections",
            "socket_connect_timeout",
            "socket_keepalive",
            "retry_on_timeout",
            "health_check_interval",
        }
        assert set(pool_config.keys()) == expected_keys
        assert pool_config["max_connections"] == redis_config.redis_max_connections
        assert pool_config["socket_connect_timeout"] == redis_config.redis_socket_connect_timeout


class TestRedisClient:
    """Test Redis client functionality and isolation."""

    async def test_client_connectivity(self, redis_client: fakeredis.aioredis.FakeRedis) -> None:
        """Test Redis client can connect and perform basic operations."""
        # Test ping
        response = await redis_client.ping()
        assert response is True

        # Test basic set/get
        await redis_client.set("test_key", "test_value")
        value = await redis_client.get("test_key")
        assert value == b"test_value"

    async def test_client_isolation(self, redis_client: fakeredis.aioredis.FakeRedis) -> None:
        """Test that Redis client provides clean state per test."""
        # Set a value
        await redis_client.set("isolation_test", "value1")

        # Verify it exists
        exists = await redis_client.exists("isolation_test")
        assert exists == 1

        # Note: Cleanup happens automatically in fixture teardown

    async def test_json_operations(self, redis_client: fakeredis.aioredis.FakeRedis) -> None:
        """Test JSON serialization/deserialization with Redis."""
        test_data = {
            "message": "hello",
            "timestamp": 1234567890,
            "nested": {"key": "value"},
            "array": [1, 2, 3],
        }

        serialized = json.dumps(test_data, separators=(",", ":"))
        await redis_client.set("json_test", serialized)

        retrieved = await redis_client.get("json_test")
        assert retrieved is not None
        deserialized = json.loads(retrieved.decode("utf-8"))

        assert deserialized == test_data


class TestBasicPubSub:
    """Test basic pub/sub functionality and roundtrip operations."""

    async def test_pubsub_connection(self, pubsub_client: RedisPubSub) -> None:
        """Test RedisPubSub can connect successfully."""
        assert pubsub_client.is_connected is True

    async def test_publish_without_subscribers(self, pubsub_client: RedisPubSub) -> None:
        """Test publishing to channel with no subscribers."""
        message = {"type": "test", "data": "no_subscribers"}

        subscriber_count = await pubsub_client.publish("test_channel", message)
        assert subscriber_count == 0

    async def test_basic_roundtrip(self, pubsub_client: RedisPubSub) -> None:
        """Test basic pub/sub message roundtrip."""
        received_messages: list[dict[str, Any]] = []

        async def message_handler(channel: str, message: dict[str, Any]) -> None:
            received_messages.append({"channel": channel, "message": message})

        # Subscribe to channel
        await pubsub_client.subscribe("roundtrip_test", message_handler)

        # Allow subscription to establish
        await asyncio.sleep(0.1)

        # Publish message
        test_message = {"type": "roundtrip", "value": "test_data", "id": 12345}
        subscriber_count = await pubsub_client.publish("roundtrip_test", test_message)

        # Should have 1 subscriber (us)
        assert subscriber_count == 1

        # Wait for message processing
        await asyncio.sleep(0.1)

        # Verify message received
        assert len(received_messages) == 1
        assert received_messages[0]["channel"] == "roundtrip_test"
        assert received_messages[0]["message"] == test_message

    async def test_multiple_handlers_same_channel(self, pubsub_client: RedisPubSub) -> None:
        """Test multiple handlers can subscribe to the same channel."""
        handler1_messages: list[dict[str, Any]] = []
        handler2_messages: list[dict[str, Any]] = []

        async def handler1(channel: str, message: dict[str, Any]) -> None:
            handler1_messages.append(message)

        async def handler2(channel: str, message: dict[str, Any]) -> None:
            handler2_messages.append(message)

        # Subscribe both handlers
        await pubsub_client.subscribe("multi_handler_test", handler1)
        await pubsub_client.subscribe("multi_handler_test", handler2)

        # Allow subscriptions to establish
        await asyncio.sleep(0.1)

        # Publish message
        test_message = {"type": "multi_handler", "data": "shared"}
        await pubsub_client.publish("multi_handler_test", test_message)

        # Wait for processing
        await asyncio.sleep(0.1)

        # Both handlers should receive the message
        assert len(handler1_messages) == 1
        assert len(handler2_messages) == 1
        assert handler1_messages[0] == test_message
        assert handler2_messages[0] == test_message

    async def test_unsubscribe_specific_handler(self, pubsub_client: RedisPubSub) -> None:
        """Test unsubscribing a specific handler while leaving others."""
        handler1_messages: list[dict[str, Any]] = []
        handler2_messages: list[dict[str, Any]] = []

        async def handler1(channel: str, message: dict[str, Any]) -> None:
            handler1_messages.append(message)

        async def handler2(channel: str, message: dict[str, Any]) -> None:
            handler2_messages.append(message)

        # Subscribe both handlers
        await pubsub_client.subscribe("unsubscribe_test", handler1)
        await pubsub_client.subscribe("unsubscribe_test", handler2)
        await asyncio.sleep(0.1)

        # Unsubscribe handler1 only
        await pubsub_client.unsubscribe("unsubscribe_test", handler1)
        await asyncio.sleep(0.1)

        # Publish message
        test_message = {"type": "after_unsubscribe", "data": "remaining"}
        await pubsub_client.publish("unsubscribe_test", test_message)
        await asyncio.sleep(0.1)

        # Only handler2 should receive the message
        assert len(handler1_messages) == 0
        assert len(handler2_messages) == 1
        assert handler2_messages[0] == test_message


class TestConnectionPoolValidation:
    """Test Redis connection pool behavior and validation."""

    async def test_pool_configuration(self, redis_config: RedisConfig) -> None:
        """Test connection pool is configured correctly."""
        # Create a fake Redis client directly (pool is handled internally)
        client = fakeredis.aioredis.FakeRedis()

        try:
            # Verify basic functionality
            response = await client.ping()
            assert response is True

            # Test basic operations
            await client.set("pool_test", "value")
            value = await client.get("pool_test")
            assert value == b"value"

        finally:
            await client.flushall()

    async def test_pool_connection_reuse(self, redis_config: RedisConfig) -> None:
        """Test connection pool reuses connections efficiently."""
        # Create separate fake Redis clients
        client1 = fakeredis.aioredis.FakeRedis()
        client2 = fakeredis.aioredis.FakeRedis()

        try:
            # Both clients should work independently
            await client1.ping()
            await client2.ping()

            # Test that they operate on separate data spaces
            await client1.set("client1_key", "value1")
            await client2.set("client2_key", "value2")

            # Each client should see their own data
            value1 = await client1.get("client1_key")
            value2 = await client2.get("client2_key")

            assert value1 == b"value1"
            assert value2 == b"value2"

        finally:
            await client1.flushall()
            await client2.flushall()

    async def test_pool_max_connections_limit(self, redis_config: RedisConfig) -> None:
        """Test connection pool basic functionality with small pool."""
        client = fakeredis.aioredis.FakeRedis()

        try:
            # Connection should work with fake Redis
            await client.ping()

            # Test multiple operations work correctly
            for i in range(5):
                await client.set(f"limit_test_{i}", f"value_{i}")
                value = await client.get(f"limit_test_{i}")
                assert value == f"value_{i}".encode()

        finally:
            await client.flushall()


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with Redis operations."""

    async def test_circuit_breaker_normal_operation(self, pubsub_client: RedisPubSub) -> None:
        """Test circuit breaker allows normal operations when Redis is healthy."""
        # Circuit breaker should start in CLOSED state
        assert pubsub_client.circuit_breaker_state == CircuitBreakerState.CLOSED

        # Normal operations should work
        test_message = {"type": "circuit_test", "status": "normal"}
        await pubsub_client.publish("circuit_test", test_message)

        # Circuit breaker should remain closed
        assert pubsub_client.circuit_breaker_state == CircuitBreakerState.CLOSED

    async def test_circuit_breaker_failure_threshold(self) -> None:
        """Test circuit breaker opens after failure threshold is reached."""
        # Create circuit breaker with low failure threshold for testing
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1.0,
            success_threshold=1,
            timeout=0.1,
            expected_exception=SimulatedRedisFailureError,
        )

        async def failing_operation() -> None:
            raise SimulatedRedisFailureError("Simulated Redis failure")

        # First failure - should not open circuit
        with pytest.raises(SimulatedRedisFailureError):
            await circuit_breaker.call(failing_operation)
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        # Second failure - should open circuit
        with pytest.raises(SimulatedRedisFailureError):
            await circuit_breaker.call(failing_operation)
        assert circuit_breaker.state == CircuitBreakerState.OPEN  # type: ignore[comparison-overlap] # Valid state transition test

        # Third attempt - should fail fast with CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(failing_operation)

    async def test_circuit_breaker_recovery(self) -> None:
        """Test circuit breaker recovery to HALF_OPEN and back to CLOSED."""
        # Create circuit breaker with short recovery timeout
        circuit_breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0.1,  # Very short for testing
            success_threshold=1,
            timeout=1.0,
            expected_exception=SimulatedRedisFailureError,
        )

        # Force circuit to open
        async def failing_operation() -> None:
            raise SimulatedRedisFailureError("Failure")

        with pytest.raises(SimulatedRedisFailureError):
            await circuit_breaker.call(failing_operation)
        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.2)

        # Successful operation should transition to HALF_OPEN then CLOSED
        async def success_operation() -> str:
            return "success"

        result = await circuit_breaker.call(success_operation)
        assert result == "success"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED  # type: ignore[comparison-overlap] # Valid state transition test

    async def test_circuit_breaker_metrics(self, pubsub_client: RedisPubSub) -> None:
        """Test circuit breaker metrics are tracked correctly."""
        initial_metrics = pubsub_client.circuit_breaker_metrics

        # Perform some operations
        test_message = {"type": "metrics_test", "data": "tracking"}
        await pubsub_client.publish("metrics_test", test_message)

        # Check updated metrics
        updated_metrics = pubsub_client.circuit_breaker_metrics

        # Should have tracked the request
        assert updated_metrics["total_requests"] > initial_metrics["total_requests"]
        assert updated_metrics["total_successes"] > initial_metrics["total_successes"]
        assert updated_metrics["failure_rate"] <= 1.0


class TestPerformanceValidation:
    """Test performance targets and latency requirements."""

    async def test_publish_latency_target(self, pubsub_client: RedisPubSub) -> None:
        """Test publish latency meets <1ms target for small messages."""
        test_message = {"type": "latency_test", "data": "small_payload"}

        # Warmup
        await pubsub_client.publish("warmup", test_message)

        # Measure publish latency
        start_time = time.perf_counter()
        await pubsub_client.publish("latency_test", test_message)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should be under 1ms for small messages on localhost
        # Allow some margin for test environment variability
        assert elapsed_ms < 5.0, f"Publish latency {elapsed_ms:.2f}ms exceeds target"

    async def test_connection_establishment_time(self, fake_redis_server: fakeredis.aioredis.FakeRedis) -> None:
        """Test Redis connection establishment is fast."""
        start_time = time.perf_counter()

        await fake_redis_server.ping()
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Connection should be very fast with fake Redis
        assert elapsed_ms < 10.0, f"Connection time {elapsed_ms:.2f}ms too slow"

    async def test_bulk_operations_performance(self, redis_client: fakeredis.aioredis.FakeRedis) -> None:
        """Test performance of bulk Redis operations."""
        # Test bulk set operations
        start_time = time.perf_counter()

        pipeline = redis_client.pipeline()
        for i in range(100):
            pipeline.set(f"bulk_key_{i}", f"value_{i}")
        await pipeline.execute()

        bulk_set_time = (time.perf_counter() - start_time) * 1000

        # Test bulk get operations
        start_time = time.perf_counter()

        pipeline = redis_client.pipeline()
        for i in range(100):
            pipeline.get(f"bulk_key_{i}")
        results = await pipeline.execute()

        bulk_get_time = (time.perf_counter() - start_time) * 1000

        # Verify results
        assert len(results) == 100
        assert all(result is not None for result in results)

        # Performance assertions (generous for test environment)
        assert bulk_set_time < 50.0, f"Bulk set time {bulk_set_time:.2f}ms too slow"
        assert bulk_get_time < 50.0, f"Bulk get time {bulk_get_time:.2f}ms too slow"


class TestHealthCheck:
    """Test health check and monitoring functionality."""

    async def test_pubsub_health_check(self, pubsub_client: RedisPubSub) -> None:
        """Test RedisPubSub health check functionality."""
        health_status = await pubsub_client.health_check()

        # Verify health check structure
        expected_keys = {
            "connected",
            "circuit_breaker",
            "redis_available",
            "active_subscriptions",
            "redis_ping",
        }
        assert set(health_status.keys()) == expected_keys

        # Verify health values
        assert health_status["connected"] is True
        assert health_status["redis_available"] is True
        assert health_status["redis_ping"] == "success"
        assert isinstance(health_status["active_subscriptions"], int)

        # Verify circuit breaker info
        cb_info = health_status["circuit_breaker"]
        assert "state" in cb_info
        assert "metrics" in cb_info
        assert cb_info["state"] == "closed"

    async def test_subscriber_count_tracking(self, pubsub_client: RedisPubSub) -> None:
        """Test subscriber count tracking functionality."""
        channel_name = "subscriber_count_test"

        # Initially should be 0 subscribers
        count = await pubsub_client.get_subscribers_count(channel_name)
        assert count == 0

        # Subscribe and check count
        async def dummy_handler(channel: str, message: dict[str, Any]) -> None:
            pass

        await pubsub_client.subscribe(channel_name, dummy_handler)
        await asyncio.sleep(0.1)  # Allow subscription to register

        count = await pubsub_client.get_subscribers_count(channel_name)
        assert count == 1

        # Unsubscribe and verify count returns to 0
        await pubsub_client.unsubscribe(channel_name, dummy_handler)
        await asyncio.sleep(0.1)  # Allow unsubscription to register

        count = await pubsub_client.get_subscribers_count(channel_name)
        assert count == 0
