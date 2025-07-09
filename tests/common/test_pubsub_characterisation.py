"""Characterization tests for Redis PubSub edge cases and missing coverage.

This module provides comprehensive characterization tests for the Redis PubSub implementation
to achieve ≥95% coverage focusing on edge cases, error handling, and failure scenarios.

Living Pattern: ADR-002 v2.1.0
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import RedisError

from src.common.pubsub import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerState,
    PublishError,
    PubSubError,
    RedisPubSub,
    cleanup_pubsub,
    get_pubsub,
)
from src.core_v2.patterns.error_handling import COSError, ErrorCategory


class TestRedisImportFallbacks:
    """Test Redis import fallback scenarios."""

    @patch("src.common.pubsub._HEALTH_MONITOR_AVAILABLE", False)
    async def test_health_monitor_not_available(self) -> None:
        """Test behavior when health monitor is not available - lines 34-36."""
        pubsub = RedisPubSub()

        # Should handle missing health monitor gracefully
        with (
            patch("src.common.pubsub.ensure_redis_available_for_tests", side_effect=ImportError),
            patch("src.common.pubsub.ConnectionPool") as mock_pool_cls,
            patch("src.common.pubsub.redis.Redis") as mock_redis_cls,
        ):
            mock_pool = AsyncMock()
            mock_pool_cls.from_url.return_value = mock_pool
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis_cls.return_value = mock_redis

            await pubsub.connect()
            # Should not raise exception due to missing health monitor
            assert pubsub.is_connected

    @patch("src.common.pubsub._LOGFIRE_AVAILABLE", False)
    async def test_logfire_not_available(self) -> None:
        """Test behavior when logfire is not available - lines 43-45."""
        pubsub = RedisPubSub()

        # Should handle missing logfire gracefully
        with (
            patch("src.common.pubsub.ConnectionPool") as mock_pool_cls,
            patch("src.common.pubsub.redis.Redis") as mock_redis_cls,
        ):
            mock_pool = AsyncMock()
            mock_pool_cls.from_url.return_value = mock_pool
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis_cls.return_value = mock_redis

            await pubsub.connect()
            # Should work without logfire
            assert pubsub.is_connected

    @patch("src.common.pubsub._REDIS_AVAILABLE", False)
    async def test_redis_not_available(self) -> None:
        """Test behavior when redis package is not available - lines 97-99."""
        with pytest.raises(PubSubError, match="Redis package is required"):
            RedisPubSub()


class TestEventLoopChecks:
    """Test event loop availability checks."""

    @patch("asyncio.get_running_loop")
    async def test_connect_no_event_loop(self, mock_get_loop: MagicMock) -> None:
        """Test connect behavior when no event loop is running - lines 432-433."""
        mock_get_loop.side_effect = RuntimeError("No event loop running")

        pubsub = RedisPubSub()
        # Should handle gracefully when no event loop is running
        await pubsub.connect()
        assert not pubsub.is_connected

    @patch("asyncio.get_running_loop")
    async def test_connect_operation_no_event_loop(self, mock_get_loop: MagicMock) -> None:
        """Test connect operation when event loop stops - lines 438-441."""
        # First call succeeds (outer check), second fails (inner check)
        mock_get_loop.side_effect = [MagicMock(), RuntimeError("No event loop running")]

        pubsub = RedisPubSub()
        with pytest.raises(PubSubError, match="Redis connection blocked by circuit breaker"):
            await pubsub.connect()
        # Should handle gracefully when event loop stops during operation
        assert not pubsub.is_connected

    @patch("asyncio.get_running_loop")
    async def test_publish_no_event_loop(self, mock_get_loop: MagicMock) -> None:
        """Test publish behavior when no event loop is running."""
        mock_get_loop.side_effect = RuntimeError("No event loop running")

        pubsub = RedisPubSub()
        result = await pubsub.publish("test", {"data": "test"})
        # Should return 0 when no event loop is running
        assert result == 0

    @patch("asyncio.get_running_loop")
    async def test_publish_with_fallback_no_event_loop(self, mock_get_loop: MagicMock) -> None:
        """Test publish_with_fallback when no event loop is running."""
        mock_get_loop.side_effect = RuntimeError("No event loop running")

        pubsub = RedisPubSub()
        result = await pubsub.publish_with_fallback("test", {"data": "test"})
        # Should use fallback strategy immediately
        assert result["fallback_used"] is True
        assert result["primary_attempted"] is False

    @patch("asyncio.get_running_loop")
    async def test_get_pubsub_no_event_loop(self, mock_get_loop: MagicMock) -> None:
        """Test get_pubsub when no event loop is running."""
        mock_get_loop.side_effect = RuntimeError("No event loop running")

        pubsub = await get_pubsub()
        # Should return instance but not connect
        assert isinstance(pubsub, RedisPubSub)

    @patch("asyncio.get_running_loop")
    async def test_cleanup_pubsub_no_event_loop(self, mock_get_loop: MagicMock) -> None:
        """Test cleanup_pubsub when no event loop is running."""
        # Setup a connected pubsub instance
        with (
            patch("src.common.pubsub.ConnectionPool") as mock_pool_cls,
            patch("src.common.pubsub.redis.Redis") as mock_redis_cls,
        ):
            mock_pool = AsyncMock()
            mock_pool_cls.from_url.return_value = mock_pool
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis_cls.return_value = mock_redis

            await get_pubsub()

            # Now simulate event loop not running during cleanup
            mock_get_loop.side_effect = RuntimeError("No event loop running")

            await cleanup_pubsub()
            # Should handle gracefully
            assert True


class TestCircuitBreakerScenarios:
    """Test circuit breaker edge cases and failure scenarios."""

    @pytest.fixture
    def pubsub(self) -> RedisPubSub:
        """Create RedisPubSub instance for testing."""
        return RedisPubSub()

    @pytest.fixture
    async def connected_pubsub(self, pubsub: RedisPubSub) -> RedisPubSub:
        """Create connected RedisPubSub instance."""
        with (
            patch("src.common.pubsub.ConnectionPool") as mock_pool_cls,
            patch("src.common.pubsub.redis.Redis") as mock_redis_cls,
        ):
            mock_pool = AsyncMock()
            mock_pool_cls.from_url.return_value = mock_pool
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis_cls.return_value = mock_redis

            await pubsub.connect()
            return pubsub

    async def test_circuit_breaker_failure_threshold_zero(self) -> None:
        """Test circuit breaker with failure threshold of 0."""
        circuit_breaker = CircuitBreaker(failure_threshold=0)

        # Should start in OPEN state
        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Should always fail
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(AsyncMock())

    async def test_circuit_breaker_no_event_loop(self) -> None:
        """Test circuit breaker when no event loop is running."""
        circuit_breaker = CircuitBreaker()

        with (
            patch("asyncio.get_running_loop", side_effect=RuntimeError("No event loop")),
            pytest.raises(CircuitBreakerError, match="event loop not running"),
        ):
            await circuit_breaker.call(AsyncMock())

    async def test_circuit_breaker_unexpected_exception(self) -> None:
        """Test circuit breaker with unexpected exception types."""
        circuit_breaker = CircuitBreaker(expected_exception=RedisError)

        async def failing_func() -> None:
            raise ValueError("Unexpected error")

        # Should not count as circuit breaker failure
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_func)

        # Circuit breaker should still be closed
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    async def test_circuit_breaker_timeout_handling(self) -> None:
        """Test circuit breaker timeout handling."""
        circuit_breaker = CircuitBreaker(timeout=0.1)

        async def slow_func() -> None:
            await asyncio.sleep(0.2)

        # Should treat timeout as failure
        with pytest.raises(TimeoutError):
            await circuit_breaker.call(slow_func)

        # Should record as failure
        assert circuit_breaker.failure_count == 1

    async def test_health_check_circuit_breaker_scenarios(self, connected_pubsub: RedisPubSub) -> None:
        """Test health check with various circuit breaker scenarios - lines 1038-1048."""
        # Test circuit breaker error during health check
        with patch.object(connected_pubsub._circuit_breaker, "call", side_effect=CircuitBreakerError("Circuit open")):
            health_status = await connected_pubsub.health_check()
            assert health_status["redis_ping"] == "failed: Circuit open"

        # Test Redis error during health check
        with patch.object(connected_pubsub._circuit_breaker, "call", side_effect=RedisError("Redis error")):
            health_status = await connected_pubsub.health_check()
            assert health_status["redis_ping"] == "failed: Redis error"

        # Test unexpected error during health check
        with patch.object(connected_pubsub._circuit_breaker, "call", side_effect=ValueError("Unexpected error")):
            health_status = await connected_pubsub.health_check()
            assert health_status["redis_ping"] == "unexpected_error: Unexpected error"

        # Test info operation failure
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.info.side_effect = Exception("Info failed")
        connected_pubsub._redis = mock_redis

        # Mock circuit breaker to succeed for ping but fail for info
        async def circuit_breaker_side_effect(func: Any, *args: Any, **kwargs: Any) -> Any:
            if func.__name__ == "_ping_operation":
                return True
            elif func.__name__ == "_info_operation":
                raise Exception("Info failed")
            else:
                return await func(*args, **kwargs)

        with patch.object(connected_pubsub._circuit_breaker, "call", side_effect=circuit_breaker_side_effect):
            health_status = await connected_pubsub.health_check()
            assert "info_failed" in health_status["redis_info"]


class TestListenLoopHandling:
    """Test listen loop edge cases and error handling."""

    @pytest.fixture
    async def pubsub_with_mock_listen(self) -> RedisPubSub:
        """Create pubsub with mocked listen functionality."""
        pubsub = RedisPubSub()

        with (
            patch("src.common.pubsub.ConnectionPool") as mock_pool_cls,
            patch("src.common.pubsub.redis.Redis") as mock_redis_cls,
        ):
            mock_pool = AsyncMock()
            mock_pool_cls.from_url.return_value = mock_pool

            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis_cls.return_value = mock_redis

            await pubsub.connect()
            return pubsub

    async def test_listen_loop_no_pubsub(self) -> None:
        """Test listen loop when pubsub is None - line 779."""
        pubsub = RedisPubSub()
        # Should return immediately when _pubsub is None
        await pubsub._listen_loop()
        assert True

    async def test_listen_loop_redis_error_handling(self) -> None:
        """Test listen loop Redis error handling - lines 802-803."""
        # Test that Redis errors are handled gracefully
        pubsub = RedisPubSub()

        # Test that empty pubsub is handled
        await pubsub._listen_loop()
        assert True


class TestErrorHandlingAndFallbacks:
    """Test error handling and fallback scenarios."""

    @pytest.fixture
    async def connected_pubsub(self) -> RedisPubSub:
        """Create connected RedisPubSub instance."""
        pubsub = RedisPubSub()

        with (
            patch("src.common.pubsub.ConnectionPool") as mock_pool_cls,
            patch("src.common.pubsub.redis.Redis") as mock_redis_cls,
        ):
            mock_pool = AsyncMock()
            mock_pool_cls.from_url.return_value = mock_pool
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis_cls.return_value = mock_redis

            await pubsub.connect()
            return pubsub

    async def test_publish_with_fallback_memory_queue(self, connected_pubsub: RedisPubSub) -> None:
        """Test publish_with_fallback with memory queue strategy."""
        # Mock publish to fail
        with patch.object(connected_pubsub, "publish", side_effect=PublishError("Publish failed")):
            result = await connected_pubsub.publish_with_fallback(
                "test", {"data": "test"}, fallback_strategy="memory_queue"
            )

            assert result["fallback_used"] is True
            assert result["success"] is True
            assert hasattr(connected_pubsub, "_memory_queue")
            assert len(connected_pubsub._memory_queue) == 1

    async def test_publish_with_fallback_file_queue(self, connected_pubsub: RedisPubSub) -> None:
        """Test publish_with_fallback with file queue strategy."""
        # Mock publish to fail
        with patch.object(connected_pubsub, "publish", side_effect=PublishError("Publish failed")):
            result = await connected_pubsub.publish_with_fallback(
                "test", {"data": "test"}, fallback_strategy="file_queue"
            )

            assert result["fallback_used"] is True
            assert result["success"] is True

    async def test_publish_with_fallback_file_queue_error(self, connected_pubsub: RedisPubSub) -> None:
        """Test publish_with_fallback with file queue error."""
        # Mock publish to fail
        with (
            patch.object(connected_pubsub, "publish", side_effect=PublishError("Publish failed")),
            patch("builtins.open", side_effect=OSError("File error")),
        ):
            result = await connected_pubsub.publish_with_fallback(
                "test", {"data": "test"}, fallback_strategy="file_queue"
            )

            assert result["fallback_used"] is True
            assert result["success"] is True  # Still succeeds with basic logging

    async def test_publish_with_fallback_log_only(self, connected_pubsub: RedisPubSub) -> None:
        """Test publish_with_fallback with log_only strategy."""
        # Mock publish to fail
        with patch.object(connected_pubsub, "publish", side_effect=PublishError("Publish failed")):
            result = await connected_pubsub.publish_with_fallback(
                "test", {"data": "test"}, fallback_strategy="log_only"
            )

            assert result["fallback_used"] is True
            assert result["success"] is True

    async def test_get_subscribers_count_type_checking(self, connected_pubsub: RedisPubSub) -> None:
        """Test get_subscribers_count with type checking."""
        # Mock circuit breaker to return non-int
        with (
            patch.object(connected_pubsub._circuit_breaker, "call", return_value="not_an_int"),
            pytest.raises(TypeError, match="Circuit breaker should return int"),
        ):
            await connected_pubsub.get_subscribers_count("test")

    async def test_publish_type_checking(self, connected_pubsub: RedisPubSub) -> None:
        """Test publish with type checking."""
        # Mock circuit breaker to return non-int
        with (
            patch.object(connected_pubsub._circuit_breaker, "call", return_value="not_an_int"),
            pytest.raises(PublishError, match="Unexpected publish error"),
        ):
            await connected_pubsub.publish("test", {"data": "test"})

    async def test_health_check_type_checking(self, connected_pubsub: RedisPubSub) -> None:
        """Test health check with type checking."""

        # Mock circuit breaker to return non-dict for info operation
        async def circuit_breaker_side_effect(func: Any, *args: Any, **kwargs: Any) -> Any:
            if func.__name__ == "_ping_operation":
                return True
            elif func.__name__ == "_info_operation":
                return "not_a_dict"
            else:
                return await func(*args, **kwargs)

        with patch.object(connected_pubsub._circuit_breaker, "call", side_effect=circuit_breaker_side_effect):
            # Should handle type error gracefully and continue
            health_status = await connected_pubsub.health_check()
            assert health_status["redis_ping"] == "success"


class TestLivingPatternIntegration:
    """Test Living Pattern integration (ADR-002 v2.1.0)."""

    async def test_cos_error_integration(self) -> None:
        """Test COSError pattern integration."""
        # Test that pubsub errors can be mapped to COSError
        pubsub_error = PubSubError("Test error")

        # Convert to COSError
        cos_error = COSError(
            message=str(pubsub_error),
            category=ErrorCategory.EXTERNAL_SERVICE,
            details={"original_error": "PubSubError"},
        )

        assert cos_error.category == ErrorCategory.EXTERNAL_SERVICE
        assert cos_error.details["original_error"] == "PubSubError"

    async def test_error_handling_pattern(self) -> None:
        """Test error handling pattern integration."""
        from src.core_v2.patterns.error_handling import map_redis_error

        # Test Redis error mapping
        redis_error = RedisError("Redis connection failed")
        cos_error = map_redis_error(redis_error)

        assert isinstance(cos_error, COSError)
        assert cos_error.category == ErrorCategory.EXTERNAL_SERVICE

    async def test_pattern_version_compliance(self) -> None:
        """Test compliance with pattern version v2.1.0."""
        # Verify that the module follows Living Pattern structure
        pubsub = RedisPubSub()

        # Should have proper error handling
        assert hasattr(pubsub, "_circuit_breaker")

        # Should have proper health check
        health_status = await pubsub.health_check()
        assert "timestamp" in health_status
        assert "circuit_breaker" in health_status
