# Test file - configured per-file ignores in ruff.toml handle common test patterns
"""Comprehensive tests for enhanced Redis error handling and Logfire integration.

This module tests the new error handling features including:
- Structured error metrics and logging
- Logfire span integration and tracing
- Correlation ID tracking across operations
- Graceful degradation with fallback strategies
- Enhanced health check functionality
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.pubsub import (
    CircuitBreakerError,
    PublishError,
    RedisOperationMetrics,
    RedisPubSub,
    correlation_id,
)

# mypy: disable-error-code="attr-defined,method-assign,assignment,arg-type"


@pytest.fixture
async def enhanced_pubsub() -> AsyncGenerator[RedisPubSub, None]:
    """Create RedisPubSub instance with enhanced error handling."""
    pubsub = RedisPubSub()

    # Mock Redis client to avoid actual connections
    mock_redis = AsyncMock()
    mock_pool = AsyncMock()

    pubsub._redis = mock_redis
    pubsub._pool = mock_pool
    pubsub._connected = True

    # Set up default successful responses
    mock_redis.publish.return_value = 1
    mock_redis.ping.return_value = True
    mock_redis.info.return_value = {
        "connected_clients": 5,
        "used_memory": 1024000,
        "redis_version": "7.0.0",
        "uptime_in_seconds": 3600,
    }

    yield pubsub

    await pubsub.disconnect()


@pytest.fixture
def mock_logfire() -> Any:
    """Mock Logfire functionality for testing."""
    with patch("src.common.pubsub.logfire") as mock_logfire, patch("src.common.pubsub._LOGFIRE_AVAILABLE", True):
        # Mock span context manager
        mock_span = MagicMock()
        mock_span.__aenter__ = AsyncMock(return_value=mock_span)
        mock_span.__aexit__ = AsyncMock(return_value=None)
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=None)
        mock_span.set_attribute = MagicMock()
        mock_span.set_attributes = MagicMock()
        mock_span.record_exception = MagicMock()

        mock_logfire.span.return_value = mock_span
        mock_logfire.info = MagicMock()
        mock_logfire.warning = MagicMock()
        mock_logfire.error = MagicMock()
        mock_logfire.debug = MagicMock()

        yield mock_logfire


class TestRedisOperationMetrics:
    """Test the RedisOperationMetrics dataclass functionality."""

    def test_metrics_initialization(self) -> None:
        """Test proper initialization of operation metrics."""
        metrics = RedisOperationMetrics(
            operation="PUBLISH", channel="test_channel", correlation_id="test-correlation-123"
        )

        assert metrics.operation == "PUBLISH"
        assert metrics.channel == "test_channel"
        assert metrics.correlation_id == "test-correlation-123"
        assert metrics.success is False
        assert metrics.error_type is None
        assert metrics.duration_ms is None
        assert isinstance(metrics.start_time, float)

    def test_metrics_completion_success(self) -> None:
        """Test marking metrics as completed successfully."""
        metrics = RedisOperationMetrics(operation="GET")

        # Simulate some operation time
        time.sleep(0.001)
        metrics.mark_completed(success=True)

        assert metrics.success is True
        assert metrics.error_type is None
        assert metrics.error_message is None
        assert metrics.duration_ms is not None
        assert metrics.duration_ms > 0

    def test_metrics_completion_with_error(self) -> None:
        """Test marking metrics as completed with error."""
        metrics = RedisOperationMetrics(operation="PUBLISH")

        test_error = ValueError("Test error message")
        metrics.mark_completed(success=False, error=test_error)

        assert metrics.success is False
        assert metrics.error_type == "ValueError"
        assert metrics.error_message == "Test error message"
        assert metrics.duration_ms is not None

    def test_metrics_to_dict(self) -> None:
        """Test conversion of metrics to dictionary."""
        metrics = RedisOperationMetrics(operation="PUBLISH", channel="test_channel", correlation_id="test-123")
        metrics.message_size_bytes = 1024
        metrics.subscriber_count = 3

        metrics_dict = metrics.to_dict()

        assert metrics_dict["operation"] == "PUBLISH"
        assert metrics_dict["channel"] == "test_channel"
        assert metrics_dict["correlation_id"] == "test-123"
        assert metrics_dict["message_size_bytes"] == 1024
        assert metrics_dict["subscriber_count"] == 3
        assert "start_time" in metrics_dict


class TestEnhancedPublishMethod:
    """Test enhanced publish method with error handling and observability."""

    async def test_publish_with_correlation_id(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test publish method with explicit correlation ID."""
        test_correlation_id = "test-correlation-123"
        test_message = {"test": "message", "id": 1}

        result = await enhanced_pubsub.publish("test_channel", test_message, correlation_id=test_correlation_id)

        assert result == 1

        # Verify Logfire span was created with correct attributes
        mock_logfire.span.assert_called_once()
        span_call = mock_logfire.span.call_args
        assert "Redis PUBLISH test_channel" in span_call[0][0]
        assert span_call[1]["correlation_id"] == test_correlation_id

    async def test_publish_generates_correlation_id(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test publish method generates correlation ID when not provided."""
        test_message = {"test": "message", "id": 2}

        result = await enhanced_pubsub.publish("test_channel", test_message)

        assert result == 1

        # Verify correlation ID was generated
        mock_logfire.span.assert_called_once()
        span_call = mock_logfire.span.call_args
        assert "correlation_id" in span_call[1]
        assert len(span_call[1]["correlation_id"]) > 0

    async def test_publish_serialization_error(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test publish method handles JSON serialization errors."""
        # Create non-serializable message
        non_serializable = {"function": lambda x: x}

        with pytest.raises(PublishError, match=r".*serialize.*"):
            await enhanced_pubsub.publish("test_channel", non_serializable)

        # Verify error was logged to Logfire
        mock_logfire.error.assert_called()
        error_call = mock_logfire.error.call_args
        assert "Unexpected publish error" in error_call[0][0]

    async def test_publish_redis_error_handling(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test publish method handles Redis errors properly."""
        from src.common.pubsub import RedisError

        # Configure mock to raise Redis error
        enhanced_pubsub._redis.publish.side_effect = RedisError("Redis connection failed")

        test_message = {"test": "message"}

        with pytest.raises(PublishError, match="Failed to publish message"):
            await enhanced_pubsub.publish("test_channel", test_message)

        # Verify error was logged to Logfire
        mock_logfire.error.assert_called()
        error_call = mock_logfire.error.call_args
        assert "Redis publish operation failed" in error_call[0][0]

    async def test_publish_circuit_breaker_error(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test publish method handles circuit breaker errors."""
        from src.common.pubsub import CircuitBreakerState

        # Configure circuit breaker to be open
        enhanced_pubsub._circuit_breaker._state = CircuitBreakerState.OPEN
        enhanced_pubsub._circuit_breaker._next_attempt_time = time.time() + 60

        test_message = {"test": "message"}

        with pytest.raises(PublishError, match="Publish blocked by circuit breaker"):
            await enhanced_pubsub.publish("test_channel", test_message)

        # Verify error was logged to Logfire
        mock_logfire.error.assert_called()

    async def test_publish_performance_warning(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test publish method logs performance warnings for slow operations."""

        # Configure mock to simulate slow operation
        async def slow_publish(*args: Any, **kwargs: Any) -> int:
            await asyncio.sleep(0.006)  # 6ms delay - exceeds 5ms threshold
            return 1

        enhanced_pubsub._redis.publish = slow_publish

        test_message = {"test": "message"}

        result = await enhanced_pubsub.publish("test_channel", test_message)
        assert result == 1

        # Verify performance warning was logged
        mock_logfire.warning.assert_called()
        warning_call = mock_logfire.warning.call_args
        assert "Publish latency exceeded target" in warning_call[0][0]


class TestEnhancedHealthCheck:
    """Test enhanced health check functionality."""

    async def test_health_check_success(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test comprehensive health check with successful Redis connection."""
        test_correlation_id = "health-check-123"

        health_status = await enhanced_pubsub.health_check(correlation_id=test_correlation_id)

        # Verify health status structure
        assert health_status["correlation_id"] == test_correlation_id
        assert health_status["connected"] is True
        assert health_status["redis_ping"] == "success"
        assert health_status["redis_available"] is True
        assert "ping_duration_ms" in health_status
        assert "circuit_breaker" in health_status
        assert "redis_info" in health_status

        # Verify Redis info was collected
        redis_info = health_status["redis_info"]
        assert redis_info["connected_clients"] == 5
        assert redis_info["redis_version"] == "7.0.0"

        # Verify Logfire logging
        mock_logfire.info.assert_called()

    async def test_health_check_redis_failure(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test health check handles Redis connection failures."""
        from src.common.pubsub import RedisError

        # Configure mock to raise Redis error
        enhanced_pubsub._redis.ping.side_effect = RedisError("Connection failed")

        health_status = await enhanced_pubsub.health_check()

        # Verify failure is properly reported
        assert "failed:" in health_status["redis_ping"]
        assert "Connection failed" in health_status["redis_ping"]
        assert "ping_duration_ms" in health_status

        # Verify error was logged to Logfire
        mock_logfire.error.assert_called()

    async def test_health_check_info_command_failure(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test health check handles Redis INFO command failures."""
        # Configure ping to succeed but info to fail
        enhanced_pubsub._redis.info.side_effect = Exception("INFO command failed")

        health_status = await enhanced_pubsub.health_check()

        # Verify ping succeeded but info failed
        assert health_status["redis_ping"] == "success"
        assert "info_failed:" in str(health_status["redis_info"])

        # Verify warning was logged for info failure
        mock_logfire.warning.assert_called()

    async def test_health_check_not_connected(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test health check when Redis is not connected."""
        enhanced_pubsub._connected = False
        enhanced_pubsub._redis = None

        health_status = await enhanced_pubsub.health_check()

        assert health_status["connected"] is False
        assert health_status["redis_ping"] == "not_connected"
        assert health_status["ping_duration_ms"] == 0

        # Verify warning was logged
        mock_logfire.warning.assert_called()


class TestGracefulDegradation:
    """Test graceful degradation and fallback strategies."""

    async def test_publish_with_fallback_success(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test publish_with_fallback when primary Redis succeeds."""
        test_message = {"test": "message"}

        result = await enhanced_pubsub.publish_with_fallback("test_channel", test_message, fallback_strategy="log_only")

        assert result["success"] is True
        assert result["primary_attempted"] is True
        assert result["fallback_used"] is False
        assert result["subscriber_count"] == 1
        assert result["error"] is None

    async def test_publish_with_fallback_log_only(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test publish_with_fallback with log_only strategy."""
        from src.common.pubsub import RedisError

        # Configure primary to fail
        enhanced_pubsub._redis.publish.side_effect = RedisError("Redis failed")

        test_message = {"test": "message"}

        result = await enhanced_pubsub.publish_with_fallback("test_channel", test_message, fallback_strategy="log_only")

        assert result["success"] is True  # log_only considers logging as success
        assert result["fallback_used"] is True
        assert result["fallback_strategy"] == "log_only"
        assert "Redis failed" in result["error"]

    async def test_publish_with_fallback_memory_queue(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test publish_with_fallback with memory_queue strategy."""
        from src.common.pubsub import PublishError

        # Configure primary to fail
        enhanced_pubsub._redis.publish.side_effect = PublishError("Redis unavailable")

        test_message = {"test": "message", "id": 123}

        result = await enhanced_pubsub.publish_with_fallback(
            "test_channel", test_message, fallback_strategy="memory_queue"
        )

        assert result["success"] is True
        assert result["fallback_used"] is True
        assert result["fallback_strategy"] == "memory_queue"

        # Verify message was queued in memory
        assert hasattr(enhanced_pubsub, "_memory_queue")
        assert len(enhanced_pubsub._memory_queue) == 1
        queued_item = enhanced_pubsub._memory_queue[0]
        assert queued_item["channel"] == "test_channel"
        assert queued_item["message"] == test_message

    async def test_publish_with_fallback_file_queue(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test publish_with_fallback with file_queue strategy."""
        # Configure primary to fail
        enhanced_pubsub._redis.publish.side_effect = CircuitBreakerError("Circuit breaker open")

        test_message = {"test": "message"}

        result = await enhanced_pubsub.publish_with_fallback(
            "test_channel", test_message, fallback_strategy="file_queue"
        )

        assert result["success"] is True
        assert result["fallback_used"] is True
        assert result["fallback_strategy"] == "file_queue"


class TestCorrelationIdTracking:
    """Test correlation ID tracking across operations."""

    async def test_correlation_id_context_propagation(self) -> None:
        """Test correlation ID propagation through context variables."""
        test_correlation_id = "test-correlation-456"

        # Set correlation ID in context
        token = correlation_id.set(test_correlation_id)

        try:
            # Verify correlation ID is available in context
            current_id = correlation_id.get()
            assert current_id == test_correlation_id
        finally:
            correlation_id.reset(token)

    async def test_correlation_id_generation(self, enhanced_pubsub: RedisPubSub) -> None:
        """Test automatic correlation ID generation."""
        test_message = {"test": "message"}

        # Publish without explicit correlation ID
        await enhanced_pubsub.publish("test_channel", test_message)

        # Should succeed (correlation ID generated internally)
        assert enhanced_pubsub._redis.publish.called

    async def test_correlation_id_in_error_scenarios(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test correlation ID is preserved in error scenarios."""
        from src.common.pubsub import RedisError

        test_correlation_id = "error-correlation-789"
        enhanced_pubsub._redis.publish.side_effect = RedisError("Test error")

        test_message = {"test": "message"}

        with pytest.raises(PublishError):
            await enhanced_pubsub.publish("test_channel", test_message, correlation_id=test_correlation_id)

        # Verify correlation ID was included in error logs
        mock_logfire.error.assert_called()
        error_call = mock_logfire.error.call_args
        assert test_correlation_id in str(error_call)


class TestLogfireIntegration:
    """Test Logfire integration and observability features."""

    async def test_logfire_span_attributes(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test comprehensive span attributes are set."""
        test_message = {"test": "data", "size": "medium"}
        test_correlation_id = "span-test-123"

        await enhanced_pubsub.publish("test_channel", test_message, correlation_id=test_correlation_id)

        # Get the mock span instance
        span_instance = mock_logfire.span.return_value.__enter__.return_value

        # Verify span attributes were set
        span_instance.set_attributes.assert_called()
        attributes_call = span_instance.set_attributes.call_args[0][0]

        assert attributes_call["operation"] == "PUBLISH"
        assert attributes_call["channel"] == "test_channel"
        assert attributes_call["correlation_id"] == test_correlation_id
        assert attributes_call["success"] is True

    async def test_logfire_error_recording(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test exceptions are properly recorded in Logfire spans."""
        from src.common.pubsub import RedisError

        test_error = RedisError("Test Redis error")
        enhanced_pubsub._redis.publish.side_effect = test_error

        test_message = {"test": "message"}

        with pytest.raises(PublishError):
            await enhanced_pubsub.publish("test_channel", test_message)

        # Verify exception was recorded in span
        span_instance = mock_logfire.span.return_value.__enter__.return_value
        span_instance.record_exception.assert_called_with(test_error)

    @patch("src.common.pubsub._LOGFIRE_AVAILABLE", False)
    async def test_graceful_logfire_unavailable(self, enhanced_pubsub: RedisPubSub) -> None:
        """Test operations work gracefully when Logfire is unavailable."""
        test_message = {"test": "message"}

        # Should not raise any exceptions despite Logfire being unavailable
        result = await enhanced_pubsub.publish("test_channel", test_message)
        assert result == 1

    async def test_logfire_performance_metrics(self, enhanced_pubsub: RedisPubSub, mock_logfire: Any) -> None:
        """Test performance metrics are logged to Logfire."""
        test_message = {"test": "performance"}

        await enhanced_pubsub.publish("perf_channel", test_message)

        # Verify performance information was logged
        mock_logfire.info.assert_called()
        info_calls = [
            call for call in mock_logfire.info.call_args_list if "Message published successfully" in str(call)
        ]
        assert len(info_calls) > 0


class TestErrorIsolation:
    """Test error isolation and recovery patterns."""

    async def test_redis_failure_does_not_affect_application(self, enhanced_pubsub: RedisPubSub) -> None:
        """Test Redis failures are properly isolated from application logic."""
        from src.common.pubsub import RedisError

        # Configure Redis to fail
        enhanced_pubsub._redis.publish.side_effect = RedisError("Catastrophic Redis failure")

        test_message = {"test": "isolation"}

        # Should raise PublishError, not the underlying RedisError
        with pytest.raises(PublishError) as exc_info:
            await enhanced_pubsub.publish("test_channel", test_message)

        # Verify the original error is wrapped
        assert "Failed to publish message" in str(exc_info.value)
        assert "Catastrophic Redis failure" in str(exc_info.value)

    async def test_circuit_breaker_prevents_cascading_failures(self, enhanced_pubsub: RedisPubSub) -> None:
        """Test circuit breaker prevents cascading failures."""
        from src.common.pubsub import RedisError

        # Configure Redis to always fail
        enhanced_pubsub._redis.publish.side_effect = RedisError("Persistent failure")

        test_message = {"test": "cascade_prevention"}

        # First few attempts should fail normally
        for _ in range(3):
            with pytest.raises(PublishError):
                await enhanced_pubsub.publish("test_channel", test_message)

        # Circuit breaker should now be open
        from src.common.pubsub import CircuitBreakerState

        assert enhanced_pubsub._circuit_breaker.state == CircuitBreakerState.OPEN

        # Subsequent attempts should fail fast with CircuitBreakerError
        with pytest.raises(PublishError, match="circuit breaker"):
            await enhanced_pubsub.publish("test_channel", test_message)

    async def test_error_recovery_after_redis_restoration(self, enhanced_pubsub: RedisPubSub) -> None:
        """Test system recovers after Redis is restored."""
        from src.common.pubsub import RedisError

        # Configure Redis to fail initially
        call_count = 0
        original_publish = enhanced_pubsub._redis.publish

        async def failing_then_succeeding_publish(*args: Any, **kwargs: Any) -> int:
            nonlocal call_count
            call_count += 1
            if call_count <= 3:  # Fail first 3 attempts only
                raise RedisError("Temporary failure")
            result = await original_publish(*args, **kwargs)
            return int(result)

        enhanced_pubsub._redis.publish = failing_then_succeeding_publish

        test_message = {"test": "recovery"}

        # Trigger circuit breaker opening
        for _ in range(3):
            with pytest.raises(PublishError):
                await enhanced_pubsub.publish("test_channel", test_message)

        # Wait for circuit breaker recovery timeout
        enhanced_pubsub._circuit_breaker._next_attempt_time = time.time() - 1

        # Should succeed after recovery
        result = await enhanced_pubsub.publish("test_channel", test_message)
        assert result == 1
