"""Redis resilience and circuit breaker integration tests.

This module tests Redis resilience, circuit breaker state transitions,
network failure simulation, and connection pool exhaustion scenarios.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fakeredis import aioredis as fake_aioredis
from freezegun import freeze_time
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
)
from redis.exceptions import (
    RedisError,
)
from redis.exceptions import (
    TimeoutError as RedisTimeoutError,
)

from src.common.pubsub import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerState,
    PublishError,
    PubSubError,
    RedisPubSub,
    SubscribeError,
)

# Test fixtures for circuit breaker resilience testing


@pytest_asyncio.fixture(scope="function")
async def circuit_breaker() -> AsyncGenerator[CircuitBreaker, None]:
    """Create circuit breaker with test-friendly parameters."""
    breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=30.0,
        success_threshold=2,
        timeout=5.0,
    )
    yield breaker


@pytest_asyncio.fixture(scope="function")
async def fake_redis_server() -> AsyncGenerator[fake_aioredis.FakeRedis, None]:
    """Create fake Redis server for resilience testing."""
    server = fake_aioredis.FakeRedis(
        decode_responses=False,
        version=(7, 2, 0),
        # Enable connection error simulation
        connection_errors_enabled=True,
    )
    yield server
    await server.flushall()


@pytest_asyncio.fixture(scope="function")
async def pubsub_client_with_failures(fake_redis_server: fake_aioredis.FakeRedis) -> AsyncGenerator[RedisPubSub, None]:
    """Create PubSub client with failure injection capabilities."""
    with patch("src.common.pubsub.redis") as mock_redis:
        # Configure mock Redis module
        mock_redis.Redis.return_value = fake_redis_server
        mock_redis.ConnectionPool.from_url.return_value = MagicMock()

        # Ensure fake Redis is connected and ready
        await fake_redis_server.ping()

        client = RedisPubSub()
        # Set up Redis instance manually
        client._redis = fake_redis_server
        client._connected = True

        # Override circuit breaker with test-friendly settings
        client._circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5.0,  # Shorter for testing
            success_threshold=2,
            timeout=2.0,
            expected_exception=(RedisError, RedisConnectionError, RedisTimeoutError, ConnectionError),
        )
        yield client
        if client.is_connected:
            await client.disconnect()


# Circuit breaker state transition tests


class TestCircuitBreakerStateTransitions:
    """Test circuit breaker state transitions under various failure scenarios."""

    async def test_closed_to_open_transition(self, circuit_breaker: CircuitBreaker) -> None:
        """Test CLOSED → OPEN transition when failure threshold is reached."""
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        async def failing_operation() -> None:
            raise RedisConnectionError("Simulated Redis failure")

        # Generate failures up to threshold
        with pytest.raises(RedisConnectionError):
            await circuit_breaker.call(failing_operation)
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 1

        with pytest.raises(RedisConnectionError):
            await circuit_breaker.call(failing_operation)
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 2

        # Third failure should trigger OPEN state
        with pytest.raises(RedisConnectionError):
            await circuit_breaker.call(failing_operation)
        assert circuit_breaker.state == CircuitBreakerState.OPEN  # type: ignore[comparison-overlap] # Valid state transition test
        assert circuit_breaker.failure_count == 3

    async def test_open_blocks_requests(self, circuit_breaker: CircuitBreaker) -> None:
        """Test that OPEN state blocks all requests."""
        # Force circuit breaker to OPEN state
        circuit_breaker._state = CircuitBreakerState.OPEN
        circuit_breaker._next_attempt_time = time.time() + 3600  # 1 hour in future

        async def success_operation() -> str:
            return "success"

        # Requests should be blocked
        with pytest.raises(CircuitBreakerError, match="Circuit breaker is open"):
            await circuit_breaker.call(success_operation)

    @freeze_time("2024-01-01 12:00:00")
    async def test_open_to_half_open_transition(self, circuit_breaker: CircuitBreaker) -> None:
        """Test OPEN → HALF_OPEN transition after recovery timeout."""
        # Force circuit breaker to OPEN state
        circuit_breaker._state = CircuitBreakerState.OPEN
        circuit_breaker._failure_count = 3
        circuit_breaker._last_failure_time = time.time()
        circuit_breaker._next_attempt_time = time.time() + 30.0  # 30s recovery timeout

        async def success_operation() -> str:
            return "success"

        # Should be blocked initially
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(success_operation)

        # Advance time past recovery timeout
        with freeze_time("2024-01-01 12:00:35"):
            result = await circuit_breaker.call(success_operation)
            assert result == "success"
            assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    async def test_half_open_to_closed_transition(self, circuit_breaker: CircuitBreaker) -> None:
        """Test HALF_OPEN → CLOSED transition after successful operations."""
        # Set circuit breaker to HALF_OPEN state
        circuit_breaker._state = CircuitBreakerState.HALF_OPEN
        circuit_breaker._success_count = 0

        async def success_operation() -> str:
            return "success"

        # First success
        await circuit_breaker.call(success_operation)
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN
        assert circuit_breaker.success_count == 1

        # Second success should close circuit
        await circuit_breaker.call(success_operation)
        assert circuit_breaker.state == CircuitBreakerState.CLOSED  # type: ignore[comparison-overlap] # Valid state transition test
        assert circuit_breaker.success_count == 0
        assert circuit_breaker.failure_count == 0

    async def test_half_open_to_open_on_failure(self, circuit_breaker: CircuitBreaker) -> None:
        """Test HALF_OPEN → OPEN transition on any failure."""
        # Set circuit breaker to HALF_OPEN state
        circuit_breaker._state = CircuitBreakerState.HALF_OPEN
        circuit_breaker._success_count = 1

        async def failing_operation() -> None:
            raise RedisConnectionError("Failure during recovery")

        # Any failure in HALF_OPEN should transition back to OPEN
        with pytest.raises(RedisConnectionError):
            await circuit_breaker.call(failing_operation)
        assert circuit_breaker.state == CircuitBreakerState.OPEN


# Network failure simulation tests


class TestNetworkFailureSimulation:
    """Test Redis operations under simulated network failures."""

    async def test_connection_error_handling(self, pubsub_client_with_failures: RedisPubSub) -> None:
        """Test handling of Redis connection errors."""
        client = pubsub_client_with_failures

        # Mock Redis to raise connection errors
        with (
            patch.object(client._redis, "publish", side_effect=RedisConnectionError("Connection refused")),
            pytest.raises(PublishError, match="Failed to publish"),
        ):
            await client.publish("test_channel", {"message": "test"})

    async def test_timeout_error_handling(self, pubsub_client_with_failures: RedisPubSub) -> None:
        """Test handling of Redis timeout errors."""
        client = pubsub_client_with_failures

        # Directly raise timeout error instead of using slow operation
        with (
            patch.object(client._redis, "publish", side_effect=RedisTimeoutError("Operation timed out")),
            pytest.raises(PublishError, match="Failed to publish"),
        ):
            await client.publish("test_channel", {"message": "test"})

    async def test_intermittent_failures(self, pubsub_client_with_failures: RedisPubSub) -> None:
        """Test behavior under intermittent network failures."""
        client = pubsub_client_with_failures

        call_count = 0

        async def intermittent_failure(*args: Any, **kwargs: Any) -> int:
            nonlocal call_count
            call_count += 1
            if call_count <= 3:  # All three calls fail to trigger circuit breaker
                raise RedisConnectionError("Intermittent failure")
            return 1  # Success after 3 failures

        with patch.object(client._redis, "publish", side_effect=intermittent_failure):
            # First failure
            with pytest.raises(PublishError, match="Failed to publish"):
                await client.publish("test_channel", {"message": "test1"})

            # Second failure
            with pytest.raises(PublishError, match="Failed to publish"):
                await client.publish("test_channel", {"message": "test2"})

            # Third failure should trigger circuit breaker open
            with pytest.raises(PublishError, match="Failed to publish"):
                await client.publish("test_channel", {"message": "test3"})

            # Verify circuit breaker is now open
            assert client.circuit_breaker_state == CircuitBreakerState.OPEN


# PubSub error handling tests


class TestPubSubErrorHandling:
    """Test PubSub error handling under Redis unavailability."""

    async def test_publish_with_circuit_breaker_open(self, pubsub_client_with_failures: RedisPubSub) -> None:
        """Test publish behavior when circuit breaker is open."""
        client = pubsub_client_with_failures

        # Force circuit breaker to open state
        client._circuit_breaker._state = CircuitBreakerState.OPEN
        client._circuit_breaker._next_attempt_time = time.time() + 3600

        with pytest.raises(PublishError, match="Circuit breaker"):
            await client.publish("test_channel", {"message": "blocked"})

    async def test_subscribe_error_handling(self, pubsub_client_with_failures: RedisPubSub) -> None:
        """Test subscription error handling under Redis failures."""
        client = pubsub_client_with_failures

        async def mock_handler(channel: str, message: dict[str, Any]) -> None:
            pass

        # Mock Redis PubSub to raise errors
        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe.side_effect = RedisConnectionError("Subscribe failed")
        client._pubsub = mock_pubsub

        with pytest.raises(SubscribeError, match="Failed to subscribe"):
            await client.subscribe("test_channel", mock_handler)

    async def test_health_check_with_failures(self, pubsub_client_with_failures: RedisPubSub) -> None:
        """Test health check behavior under Redis failures."""
        client = pubsub_client_with_failures

        # Mock ping to fail
        with patch.object(client._redis, "ping", side_effect=RedisConnectionError("Ping failed")):
            health = await client.health_check()
            assert health["connected"] is True
            assert "failed" in health["redis_ping"]


# Connection pool exhaustion tests


class TestConnectionPoolExhaustion:
    """Test connection pool behavior under high load and exhaustion scenarios."""

    async def test_connection_pool_limits(self) -> None:
        """Test connection pool behavior at maximum capacity."""
        with patch("src.common.pubsub.redis") as mock_redis:
            # Create mocks
            mock_pool = MagicMock()
            mock_redis.ConnectionPool.from_url.return_value = mock_pool
            mock_redis_client = AsyncMock()
            mock_redis.Redis.return_value = mock_redis_client

            # Simulate ping failure (pool exhaustion)
            mock_redis_client.ping.side_effect = RedisConnectionError("Pool exhausted")

            client = RedisPubSub()
            with pytest.raises(PubSubError, match="Redis connection failed"):
                await client.connect()

    async def test_concurrent_operations_stress(self, pubsub_client_with_failures: RedisPubSub) -> None:
        """Test concurrent operations under connection pressure."""
        client = pubsub_client_with_failures

        # Create many concurrent publish operations
        async def publish_task(message_id: int) -> int | None:
            try:
                return await client.publish("stress_test", {"id": message_id})
            except Exception:
                return None

        # Run 10 concurrent operations (reduced for test reliability)
        tasks = [publish_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least some should succeed even under stress
        successful = [r for r in results if isinstance(r, int)]
        assert len(successful) > 0


# Deterministic failure timing tests with freezegun


class TestDeterministicFailureTiming:
    """Test circuit breaker timing behavior with deterministic time control."""

    @freeze_time("2024-01-01 12:00:00")
    async def test_recovery_timeout_precision(self, circuit_breaker: CircuitBreaker) -> None:
        """Test precise recovery timeout behavior."""
        # Force to OPEN state
        circuit_breaker._state = CircuitBreakerState.OPEN
        circuit_breaker._next_attempt_time = time.time() + 30.0

        async def test_operation() -> str:
            return "success"

        # Should be blocked before timeout
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(test_operation)

        # Advance time to just before timeout
        with freeze_time("2024-01-01 12:00:29.9"), pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(test_operation)

        # Advance time past timeout
        with freeze_time("2024-01-01 12:00:30.1"):
            result = await circuit_breaker.call(test_operation)
            assert result == "success"
            assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    @freeze_time("2024-01-01 12:00:00")
    async def test_exponential_backoff_timing(self, circuit_breaker: CircuitBreaker) -> None:
        """Test exponential backoff calculation accuracy."""

        async def failing_operation() -> None:
            raise RedisConnectionError("Test failure")

        # Generate failures to reach threshold (3)
        for _i in range(3):
            with pytest.raises(RedisConnectionError):
                await circuit_breaker.call(failing_operation)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Check that backoff multiplier affects next attempt time
        metrics = circuit_breaker.metrics
        next_attempt = metrics["next_attempt_time"]
        last_failure = metrics["last_failure_time"]

        # Should have base recovery timeout (30s in fixture) applied
        backoff_time = next_attempt - last_failure
        assert backoff_time >= 30.0  # At least base recovery timeout (fixture uses 30s)
        assert backoff_time < 300.0  # Reasonable upper bound

    @freeze_time("2024-01-01 12:00:00")
    async def test_state_transition_metrics(self, circuit_breaker: CircuitBreaker) -> None:
        """Test accurate state transition tracking over time."""

        async def failing_operation() -> None:
            raise RedisConnectionError("Test failure")

        async def success_operation() -> str:
            return "success"

        # Initial state
        initial_metrics = circuit_breaker.metrics
        assert initial_metrics["state_transitions"]["closed_to_open"] == 0

        # Force CLOSED → OPEN transition
        for _ in range(3):
            with pytest.raises(RedisConnectionError):
                await circuit_breaker.call(failing_operation)

        open_metrics = circuit_breaker.metrics
        assert open_metrics["state_transitions"]["closed_to_open"] == 1
        assert open_metrics["state"] == "open"

        # Advance time and test OPEN → HALF_OPEN
        with freeze_time("2024-01-01 12:00:35"):
            await circuit_breaker.call(success_operation)
            half_open_metrics = circuit_breaker.metrics
            assert half_open_metrics["state_transitions"]["open_to_half_open"] == 1

            # Complete HALF_OPEN → CLOSED transition
            await circuit_breaker.call(success_operation)
            closed_metrics = circuit_breaker.metrics
            assert closed_metrics["state_transitions"]["half_open_to_closed"] == 1
            assert closed_metrics["state"] == "closed"


# Performance validation under failure conditions


class TestFailurePerformanceValidation:
    """Test performance characteristics under various failure scenarios."""

    async def test_circuit_breaker_latency_overhead(self, circuit_breaker: CircuitBreaker) -> None:
        """Test circuit breaker adds minimal latency overhead."""

        async def fast_operation() -> str:
            return "success"

        # Measure latency with circuit breaker
        start_time = time.perf_counter()
        for _ in range(100):
            await circuit_breaker.call(fast_operation)
        total_time = time.perf_counter() - start_time

        # Circuit breaker overhead should be minimal (<1ms per operation)
        avg_overhead = (total_time / 100) * 1000
        assert avg_overhead < 1.0, f"Circuit breaker overhead {avg_overhead:.2f}ms too high"

    async def test_failure_detection_speed(self, circuit_breaker: CircuitBreaker) -> None:
        """Test circuit breaker detects failures quickly."""

        async def failing_operation() -> None:
            raise RedisConnectionError("Quick failure")

        # Measure time to open circuit
        start_time = time.perf_counter()
        for _ in range(3):  # failure_threshold = 3
            with pytest.raises(RedisConnectionError):
                await circuit_breaker.call(failing_operation)
        detection_time = (time.perf_counter() - start_time) * 1000

        assert circuit_breaker.state == CircuitBreakerState.OPEN
        # Should open circuit quickly (<10ms for 3 failures)
        assert detection_time < 10.0, f"Failure detection too slow: {detection_time:.2f}ms"

    async def test_blocked_request_performance(self, circuit_breaker: CircuitBreaker) -> None:
        """Test blocked requests fail fast in OPEN state."""
        # Force circuit to OPEN state
        circuit_breaker._state = CircuitBreakerState.OPEN
        circuit_breaker._next_attempt_time = time.time() + 3600

        async def would_be_slow_operation() -> str:
            await asyncio.sleep(1.0)  # Simulate slow operation
            return "success"

        # Measure time to reject request
        start_time = time.perf_counter()
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(would_be_slow_operation)
        rejection_time = (time.perf_counter() - start_time) * 1000

        # Should fail fast (<1ms)
        assert rejection_time < 1.0, f"Blocked request too slow: {rejection_time:.2f}ms"
