"""Tests for Circuit Breaker functionality in pubsub.py.

This module tests the circuit breaker implementation for Redis resilience,
including state transitions, failure tracking, recovery mechanisms, and
integration with Redis operations.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.common.pubsub import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerState,
    PublishError,
    PubSubError,
    RedisPubSub,
)


class TestError(Exception):
    """Specific exception for testing circuit breaker behavior."""


class TestCircuitBreaker:
    """Test cases for the CircuitBreaker class."""

    @pytest.fixture
    def circuit_breaker(self) -> CircuitBreaker:
        """Create a circuit breaker instance for testing."""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,  # Short timeout for testing
            success_threshold=2,
            timeout=0.5,
        )

    async def test_initial_state(self, circuit_breaker: CircuitBreaker) -> None:
        """Test circuit breaker initial state."""
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0

    async def test_successful_call(self, circuit_breaker: CircuitBreaker) -> None:
        """Test successful function call through circuit breaker."""

        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    async def test_failure_tracking(self, circuit_breaker: CircuitBreaker) -> None:
        """Test failure tracking and threshold behavior."""

        async def failing_func():
            raise TestError("Test failure")

        # Should remain closed for failures below threshold
        for i in range(circuit_breaker.failure_threshold - 1):
            with pytest.raises(TestError):
                await circuit_breaker.call(failing_func)
            assert circuit_breaker.state == CircuitBreakerState.CLOSED
            assert circuit_breaker.failure_count == i + 1

        # Should open after reaching failure threshold
        with pytest.raises(TestError):
            await circuit_breaker.call(failing_func)
        assert circuit_breaker.state == CircuitBreakerState.OPEN

    async def test_open_state_blocks_requests(self, circuit_breaker: CircuitBreaker) -> None:
        """Test that open circuit breaker blocks requests."""

        async def failing_func():
            raise TestError("Test failure")

        # Trigger circuit breaker to open
        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(TestError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Should block subsequent requests
        async def success_func():
            return "success"

        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(success_func)

    async def test_half_open_transition(self, circuit_breaker: CircuitBreaker) -> None:
        """Test transition from OPEN to HALF_OPEN after timeout."""

        async def failing_func():
            raise TestError("Test failure")

        # Open the circuit breaker
        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(TestError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(circuit_breaker.recovery_timeout + 0.1)

        # Next call should transition to HALF_OPEN
        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    async def test_half_open_to_closed_transition(self, circuit_breaker: CircuitBreaker) -> None:
        """Test transition from HALF_OPEN to CLOSED after enough successes."""
        # Manually set to HALF_OPEN state
        circuit_breaker._state = CircuitBreakerState.HALF_OPEN

        async def success_func():
            return "success"

        # Should remain HALF_OPEN until success threshold is reached
        for i in range(circuit_breaker.success_threshold - 1):
            result = await circuit_breaker.call(success_func)
            assert result == "success"
            assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN
            assert circuit_breaker.success_count == i + 1

        # Final success should close the circuit
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    async def test_half_open_to_open_on_failure(self, circuit_breaker: CircuitBreaker) -> None:
        """Test transition from HALF_OPEN back to OPEN on failure."""
        # Manually set to HALF_OPEN state
        circuit_breaker._state = CircuitBreakerState.HALF_OPEN

        async def failing_func():
            raise TestError("Test failure")

        # Any failure in HALF_OPEN should return to OPEN
        with pytest.raises(TestError):
            await circuit_breaker.call(failing_func)
        assert circuit_breaker.state == CircuitBreakerState.OPEN

    async def test_timeout_handling(self, circuit_breaker: CircuitBreaker) -> None:
        """Test that timeouts are treated as failures."""

        async def slow_func():
            await asyncio.sleep(circuit_breaker.timeout + 0.1)
            return "too slow"

        with pytest.raises(asyncio.TimeoutError):
            await circuit_breaker.call(slow_func)
        assert circuit_breaker.failure_count == 1

    async def test_metrics_tracking(self, circuit_breaker: CircuitBreaker) -> None:
        """Test that metrics are properly tracked."""

        async def success_func():
            return "success"

        async def failing_func():
            raise TestError("Test failure")

        # Execute some operations
        await circuit_breaker.call(success_func)

        with pytest.raises(TestError):
            await circuit_breaker.call(failing_func)

        metrics = circuit_breaker.metrics
        assert metrics["total_requests"] == 2
        assert metrics["total_successes"] == 1
        assert metrics["total_failures"] == 1
        assert metrics["failure_rate"] == 0.5
        assert metrics["state"] == CircuitBreakerState.CLOSED.value

    async def test_exponential_backoff(self, circuit_breaker: CircuitBreaker) -> None:
        """Test exponential backoff behavior."""

        async def failing_func():
            raise TestError("Test failure")

        # Open the circuit breaker
        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(TestError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Check that next attempt time increases with more failures
        first_next_attempt = circuit_breaker._next_attempt_time

        # Trigger more failures after recovery timeout
        await asyncio.sleep(circuit_breaker.recovery_timeout + 0.1)

        with pytest.raises(TestError):
            await circuit_breaker.call(failing_func)

        second_next_attempt = circuit_breaker._next_attempt_time
        assert second_next_attempt > first_next_attempt


class TestRedisPubSubCircuitBreaker:
    """Test cases for circuit breaker integration with RedisPubSub."""

    @pytest.fixture
    def mock_redis_config(self):
        """Mock Redis configuration."""
        config = Mock()
        config.redis_url = "redis://localhost:6379"
        config.redis_max_connections = 10
        config.redis_socket_connect_timeout = 5
        config.redis_socket_keepalive = True
        config.redis_retry_on_timeout = True
        config.redis_health_check_interval = 30
        return config

    @pytest.fixture
    async def pubsub_with_mocks(self, mock_redis_config: Any) -> Any:
        """Create RedisPubSub instance with mocked Redis."""
        with (
            patch("src.common.pubsub.get_redis_config", return_value=mock_redis_config),
            patch("src.common.pubsub._REDIS_AVAILABLE", True),
            patch("src.common.pubsub.redis") as mock_redis,
            patch("src.common.pubsub.ConnectionPool") as mock_pool,
        ):
            # Setup mocks
            mock_redis_instance = AsyncMock()
            mock_redis.Redis.return_value = mock_redis_instance
            mock_pool.from_url.return_value = Mock()
            pubsub = RedisPubSub()
            pubsub._redis = mock_redis_instance

            yield pubsub, mock_redis_instance

    async def test_connect_with_circuit_breaker(self, pubsub_with_mocks: Any) -> None:
        """Test connect method with circuit breaker protection."""
        pubsub, mock_redis = pubsub_with_mocks

        # Successful connection
        await pubsub.connect()
        assert pubsub._connected
        mock_redis.ping.assert_called_once()

    async def test_connect_failure_triggers_circuit_breaker(self, pubsub_with_mocks: Any) -> None:
        """Test that connection failures trigger circuit breaker."""
        pubsub, mock_redis = pubsub_with_mocks

        # Mock Redis ping to fail
        from src.common.pubsub import RedisError

        mock_redis.ping.side_effect = RedisError("Connection failed")

        # Multiple failures should trigger circuit breaker
        for _ in range(pubsub._circuit_breaker.failure_threshold):
            with pytest.raises(PubSubError):
                await pubsub.connect()

        # Circuit breaker should now be open
        assert pubsub._circuit_breaker.state == CircuitBreakerState.OPEN

    async def test_publish_with_circuit_breaker(self, pubsub_with_mocks: Any) -> None:
        """Test publish method with circuit breaker protection."""
        pubsub, mock_redis = pubsub_with_mocks
        pubsub._connected = True

        # Mock successful publish
        mock_redis.publish.return_value = 1

        result = await pubsub.publish("test_channel", {"message": "test"})
        assert result == 1
        mock_redis.publish.assert_called_once()

    async def test_publish_failure_opens_circuit_breaker(self, pubsub_with_mocks: Any) -> None:
        """Test that publish failures open circuit breaker."""
        pubsub, mock_redis = pubsub_with_mocks
        pubsub._connected = True

        # Mock Redis publish to fail
        from src.common.pubsub import RedisError

        mock_redis.publish.side_effect = RedisError("Publish failed")

        # Multiple failures should trigger circuit breaker
        for _ in range(pubsub._circuit_breaker.failure_threshold):
            with pytest.raises(PublishError):
                await pubsub.publish("test_channel", {"message": "test"})

        # Circuit breaker should now be open
        assert pubsub._circuit_breaker.state == CircuitBreakerState.OPEN

        # Next publish should be blocked by circuit breaker
        mock_redis.publish.side_effect = None  # Reset side effect
        with pytest.raises(PublishError, match="circuit breaker"):
            await pubsub.publish("test_channel", {"message": "test"})

    async def test_health_check_with_circuit_breaker(self, pubsub_with_mocks: Any) -> None:
        """Test health check method includes circuit breaker status."""
        pubsub, mock_redis = pubsub_with_mocks
        pubsub._connected = True

        health = await pubsub.health_check()

        assert "circuit_breaker" in health
        assert "state" in health["circuit_breaker"]
        assert "metrics" in health["circuit_breaker"]
        assert health["circuit_breaker"]["state"] == CircuitBreakerState.CLOSED.value

    async def test_circuit_breaker_properties(self, pubsub_with_mocks: Any) -> None:
        """Test circuit breaker property accessors."""
        pubsub, _ = pubsub_with_mocks

        assert pubsub.circuit_breaker_state == CircuitBreakerState.CLOSED

        metrics = pubsub.circuit_breaker_metrics
        assert isinstance(metrics, dict)
        assert "state" in metrics
        assert "total_requests" in metrics

    async def test_get_subscribers_count_with_circuit_breaker(self, pubsub_with_mocks: Any) -> None:
        """Test get_subscribers_count with circuit breaker protection."""
        pubsub, mock_redis = pubsub_with_mocks
        pubsub._connected = True

        # Mock successful response
        mock_redis.pubsub_numsub.return_value = {"test_channel": 5}

        count = await pubsub.get_subscribers_count("test_channel")
        assert count == 5
        mock_redis.pubsub_numsub.assert_called_once_with("test_channel")

    async def test_circuit_breaker_recovery(self, pubsub_with_mocks: Any) -> None:
        """Test circuit breaker recovery after Redis comes back online."""
        pubsub, mock_redis = pubsub_with_mocks
        pubsub._connected = True

        # Cause failures to open circuit breaker
        from src.common.pubsub import RedisError

        mock_redis.publish.side_effect = RedisError("Redis down")

        for _ in range(pubsub._circuit_breaker.failure_threshold):
            with pytest.raises(PublishError):
                await pubsub.publish("test_channel", {"message": "test"})

        assert pubsub._circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(pubsub._circuit_breaker.recovery_timeout + 0.1)

        # Redis comes back online
        mock_redis.publish.side_effect = None
        mock_redis.publish.return_value = 1

        # Should transition to HALF_OPEN and then CLOSED
        result = await pubsub.publish("test_channel", {"message": "test"})
        assert result == 1

        # After enough successes, should be closed
        for _ in range(pubsub._circuit_breaker.success_threshold - 1):
            await pubsub.publish("test_channel", {"message": "test"})

        assert pubsub._circuit_breaker.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerConfiguration:
    """Test circuit breaker configuration and edge cases."""

    async def test_custom_expected_exception(self) -> None:
        """Test circuit breaker with custom expected exception types."""

        class CustomError(Exception):
            pass

        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            expected_exception=(CustomError, ValueError),
        )

        async def custom_error_func():
            raise CustomError("Custom error")

        async def other_error_func():
            raise RuntimeError("Other error")

        # CustomError should trigger circuit breaker
        with pytest.raises(CustomError):
            await circuit_breaker.call(custom_error_func)
        assert circuit_breaker.failure_count == 1

        # RuntimeError should not trigger circuit breaker failure tracking
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(other_error_func)
        assert circuit_breaker.failure_count == 1  # Should not increment

    async def test_zero_failure_threshold(self) -> None:
        """Test circuit breaker with zero failure threshold (always open)."""
        circuit_breaker = CircuitBreaker(failure_threshold=0)

        async def any_func():
            return "success"

        # Should immediately block requests
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(any_func)

    async def test_concurrent_access(self) -> None:
        """Test circuit breaker thread safety with concurrent access."""
        circuit_breaker = CircuitBreaker(failure_threshold=5)

        async def test_func():
            await asyncio.sleep(0.01)  # Small delay
            return "success"

        # Run multiple concurrent operations
        tasks = [circuit_breaker.call(test_func) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert all(result == "success" for result in results)
        assert circuit_breaker.metrics["total_requests"] == 10
        assert circuit_breaker.metrics["total_successes"] == 10
