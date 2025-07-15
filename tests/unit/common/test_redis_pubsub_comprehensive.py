# Test file - configured per-file ignores in ruff.toml handle common test patterns
"""Comprehensive unit tests for Redis Pub/Sub with circuit breaker integration."""

import asyncio
import contextlib
import json
import os
import time
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time
from redis.exceptions import RedisError

from src.common.pubsub import (
    CircuitBreakerState,
    MessageData,
    PublishError,
    PubSubError,
    RedisPubSub,
    SubscribeError,
    cleanup_pubsub,
    get_pubsub,
)

# Add warning filters for clean test output
pytestmark = [
    pytest.mark.filterwarnings("ignore:No logs or spans will be created"),
    pytest.mark.filterwarnings("ignore::RuntimeWarning"),
]


class TestRedisPubSubComprehensive:
    """Comprehensive test suite for RedisPubSub with circuit breaker integration."""

    @pytest.fixture
    async def pubsub(self, mock_redis_config: Any, monkeypatch: Any) -> RedisPubSub:
        """Create RedisPubSub instance with mocked dependencies."""
        monkeypatch.setattr("src.common.pubsub._REDIS_AVAILABLE", True)
        # Disable health monitor for unit tests to avoid 2-second delay
        monkeypatch.setattr("src.common.pubsub._HEALTH_MONITOR_AVAILABLE", False)
        monkeypatch.setattr("src.common.pubsub.get_redis_config", lambda: mock_redis_config)
        return RedisPubSub()

    @pytest.fixture
    async def connected_pubsub(self, pubsub: RedisPubSub, fake_redis: Any) -> AsyncGenerator[RedisPubSub, None]:
        """Create connected RedisPubSub instance with fake Redis."""
        # Mock the connection setup
        with (
            patch("src.common.pubsub.ConnectionPool") as mock_pool_cls,
            patch("src.common.pubsub.redis.Redis") as mock_redis_cls,
        ):
            mock_pool = AsyncMock()
            mock_pool_cls.from_url.return_value = mock_pool

            mock_redis_cls.return_value = fake_redis

            await pubsub.connect()
            pubsub._redis = fake_redis
            yield pubsub
            await pubsub.disconnect()

    async def test_init_without_redis_available(self, monkeypatch: Any) -> None:
        """Test initialization when Redis is not available."""
        monkeypatch.setattr("src.common.pubsub._REDIS_AVAILABLE", False)

        with pytest.raises(PubSubError, match="Redis package is required"):
            RedisPubSub()

    async def test_connect_circuit_breaker_protection(self, pubsub: RedisPubSub) -> None:
        """Test connection with circuit breaker protection."""
        with patch("src.common.pubsub.ConnectionPool") as mock_pool_cls:
            # Mock to raise a RedisError that circuit breaker will catch
            mock_pool_cls.from_url.side_effect = RedisError("Connection failed")

            # Should be caught by circuit breaker and wrapped in PubSubError
            with pytest.raises(PubSubError):
                await pubsub.connect()

        assert not pubsub._connected

    async def test_connect_circuit_breaker_open(self, pubsub: RedisPubSub) -> None:
        """Test connection when circuit breaker is open."""
        # Force circuit breaker to OPEN state
        pubsub._circuit_breaker._state = CircuitBreakerState.OPEN
        pubsub._circuit_breaker._next_attempt_time = time.time() + 3600

        with pytest.raises(PubSubError, match="blocked by circuit breaker"):
            await pubsub.connect()

    async def test_publish_circuit_breaker_protection(self, connected_pubsub: RedisPubSub) -> None:
        """Test publish with circuit breaker protection."""
        # Mock Redis to fail
        connected_pubsub._redis.publish = AsyncMock(side_effect=Exception("Redis error"))

        with pytest.raises(PublishError):
            await connected_pubsub.publish("test", {"data": "test"})

    async def test_publish_performance_logging(self, connected_pubsub: RedisPubSub, caplog: Any) -> None:
        """Test publish performance logging for slow operations."""
        with freeze_time("2023-01-01 00:00:00") as frozen_time:

            async def slow_publish(*args: Any, **kwargs: Any) -> int:
                frozen_time.tick(0.002)  # Simulate 2ms delay
                return 1

            connected_pubsub._redis.publish = slow_publish

            await connected_pubsub.publish("test", {"data": "test"})

            assert "exceeded 5ms target" in caplog.text

    async def test_publish_json_serialization_edge_cases(self, connected_pubsub: RedisPubSub) -> None:
        """Test JSON serialization edge cases."""
        test_cases = [
            {},  # Empty dict
            {"unicode": "测试"},  # Unicode
            {"nested": {"deep": {"value": 123}}},  # Nested structure
            {"list": [1, 2, 3, {"nested": "value"}]},  # Mixed types
            {"null": None, "bool": True, "number": 42.5},  # Various types
        ]

        connected_pubsub._redis.publish = AsyncMock(return_value=1)

        for test_case in test_cases:
            result = await connected_pubsub.publish("test", test_case)  # type: ignore[arg-type]
            assert result == 1

    async def test_publish_non_serializable_objects(self, connected_pubsub: RedisPubSub) -> None:
        """Test publishing non-serializable objects."""

        class NonSerializable:
            pass

        test_cases = [
            {"object": NonSerializable()},
            {"function": lambda x: x},
            {"bytes": b"raw bytes"},
            {"set": {1, 2, 3}},
        ]

        for test_case in test_cases:
            with pytest.raises(PublishError):
                await connected_pubsub.publish("test", test_case)  # type: ignore[arg-type]

    async def test_subscribe_with_circuit_breaker_failure(self, connected_pubsub: RedisPubSub) -> None:
        """Test subscription when circuit breaker prevents operations."""
        # Create a mock pubsub that fails on subscribe with RedisError
        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe = AsyncMock(side_effect=RedisError("Redis subscription error"))

        # Replace the existing _pubsub with our mock
        connected_pubsub._pubsub = mock_pubsub

        async def handler(channel: str, message: MessageData) -> None:
            pass

        with pytest.raises(SubscribeError):
            await connected_pubsub.subscribe("test", handler)

    async def test_unsubscribe_edge_cases(self, connected_pubsub: RedisPubSub) -> None:
        """Test unsubscribe edge cases."""
        mock_pubsub = AsyncMock()
        connected_pubsub._pubsub = mock_pubsub

        async def handler1(channel: str, message: MessageData) -> None:
            pass

        async def handler2(channel: str, message: MessageData) -> None:
            pass

        # Test unsubscribing handler that wasn't subscribed
        await connected_pubsub.unsubscribe("nonexistent", handler1)

        # Test unsubscribing from channel with multiple handlers
        connected_pubsub._subscribers.add("test")
        connected_pubsub._handlers["test"] = [handler1, handler2]

        await connected_pubsub.unsubscribe("test", handler1)
        assert handler1 not in connected_pubsub._handlers["test"]
        assert handler2 in connected_pubsub._handlers["test"]
        assert "test" in connected_pubsub._subscribers

    async def test_message_handling_various_formats(self, connected_pubsub: RedisPubSub) -> None:
        """Test message handling with various data formats."""
        received_messages = []

        async def handler(channel: str, message: MessageData) -> None:
            received_messages.append((channel, message))

        connected_pubsub._handlers["test"] = [handler]

        test_cases = [
            # Bytes channel, bytes data
            {"channel": b"test", "data": b'{"type": "bytes"}'},
            # String channel, string data
            {"channel": "test", "data": '{"type": "string"}'},
            # Unicode data
            {"channel": "test", "data": '{"unicode": "测试"}'},
            # Large payload
            {"channel": "test", "data": json.dumps({"large": "x" * 1000})},
        ]

        for test_case in test_cases:
            await connected_pubsub._handle_message(test_case)  # type: ignore[arg-type]

        assert len(received_messages) == 4

    async def test_message_handling_malformed_data(self, connected_pubsub: RedisPubSub, caplog: Any) -> None:
        """Test message handling with malformed data."""

        async def handler(channel: str, message: MessageData) -> None:
            pass

        connected_pubsub._handlers["test"] = [handler]

        malformed_cases = [
            {"channel": "test", "data": b"invalid json"},
            {"channel": "test", "data": b'{"incomplete": '},
            {"channel": "test", "data": b"null"},
            {"channel": "test", "data": b""},
        ]

        for case in malformed_cases:
            await connected_pubsub._handle_message(case)

        # Should log decode errors
        assert "Failed to decode message" in caplog.text

    async def test_message_handling_handler_exceptions(self, connected_pubsub: RedisPubSub, caplog: Any) -> None:
        """Test message handling when handlers raise exceptions."""
        exception_count = 0

        async def failing_handler(channel: str, message: MessageData) -> None:
            nonlocal exception_count
            exception_count += 1
            raise ValueError(f"Handler error {exception_count}")

        async def working_handler(channel: str, message: MessageData) -> None:
            pass

        connected_pubsub._handlers["test"] = [failing_handler, working_handler]

        message = {"channel": "test", "data": '{"test": "data"}'}
        await connected_pubsub._handle_message(message)

        # Should log handler errors but continue processing
        assert "Error handling message" in caplog.text

    async def test_listen_loop_cancellation_scenarios(self, connected_pubsub: RedisPubSub) -> None:
        """Test listen loop cancellation in various scenarios."""

        # Create proper async iterator that can be cancelled
        class AsyncIteratorMock:
            def __init__(self) -> None:
                self.count = 0

            def __aiter__(self) -> "AsyncIteratorMock":
                return self

            async def __anext__(self) -> dict[str, Any]:
                self.count += 1
                if self.count == 1:
                    return {"type": "message", "channel": b"test", "data": b"test data"}
                # After first message, wait until cancelled
                await asyncio.sleep(0.01)  # Reduced from 10s
                return {"type": "message", "channel": b"test", "data": b"test data 2"}

        mock_pubsub = AsyncMock()
        mock_pubsub.listen = MagicMock(return_value=AsyncIteratorMock())
        connected_pubsub._pubsub = mock_pubsub

        # Start listen loop
        task = asyncio.create_task(connected_pubsub._listen_loop())
        await asyncio.sleep(0.01)  # Let it start

        # Cancel and verify graceful handling
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_listen_loop_reconnection_scenarios(self, connected_pubsub: RedisPubSub) -> None:
        """Test listen loop reconnection on various errors."""
        reconnect_attempts = 0

        # Create async iterator that fails first, then succeeds
        class ReconnectIteratorMock:
            def __init__(self, outer_test: Any) -> None:
                self.outer_test = outer_test

            def __aiter__(self) -> "ReconnectIteratorMock":
                return self

            async def __anext__(self) -> dict[str, Any]:
                nonlocal reconnect_attempts
                reconnect_attempts += 1
                if reconnect_attempts == 1:
                    raise RedisError("Connection lost")
                # Second attempt succeeds but we'll cancel it
                await asyncio.sleep(0.01)  # Will be cancelled, reduced from 10s
                return {"type": "message", "channel": b"test", "data": b"test data"}

        mock_pubsub = AsyncMock()
        mock_pubsub.listen = MagicMock(return_value=ReconnectIteratorMock(self))
        mock_pubsub.subscribe = AsyncMock()
        connected_pubsub._pubsub = mock_pubsub
        connected_pubsub._subscribers.add("test")

        with patch.object(connected_pubsub, "connect") as mock_connect:
            mock_connect.return_value = None

            # Start listen loop
            task = asyncio.create_task(connected_pubsub._listen_loop())
            await asyncio.sleep(0.02)  # Let it attempt reconnection, reduced from 0.1s
            task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await task

            # Should have attempted reconnection
            mock_connect.assert_called()

    async def test_channel_subscription_context_manager_error_handling(self, connected_pubsub: RedisPubSub) -> None:
        """Test channel subscription context manager error handling."""
        mock_pubsub = AsyncMock()
        # Replace the existing _pubsub with our mock
        connected_pubsub._pubsub = mock_pubsub

        async def handler(channel: str, message: MessageData) -> None:
            pass

        # Test exception during context
        try:
            async with connected_pubsub.channel_subscription("test") as add_handler:
                await add_handler(handler)
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should still clean up properly
        assert "test" not in connected_pubsub._subscribers

    async def test_get_subscribers_count_edge_cases(self, connected_pubsub: RedisPubSub) -> None:
        """Test get_subscribers_count edge cases."""
        # Test with empty response
        connected_pubsub._redis.pubsub_numsub = AsyncMock(return_value={})
        count = await connected_pubsub.get_subscribers_count("test")
        assert count == 0

        # Test with channel not in response
        connected_pubsub._redis.pubsub_numsub = AsyncMock(return_value={"other": 5})
        count = await connected_pubsub.get_subscribers_count("test")
        assert count == 0

    async def test_circuit_breaker_state_properties(self, connected_pubsub: RedisPubSub) -> None:
        """Test circuit breaker state properties."""
        assert connected_pubsub.circuit_breaker_state == CircuitBreakerState.CLOSED

        metrics = connected_pubsub.circuit_breaker_metrics
        assert "state" in metrics
        assert "total_requests" in metrics

    async def test_health_check_comprehensive(self, connected_pubsub: RedisPubSub) -> None:
        """Test comprehensive health check functionality."""
        # Test healthy state
        connected_pubsub._redis.ping = AsyncMock()
        health = await connected_pubsub.health_check()

        assert health["connected"] is True
        assert health["redis_available"] is True
        assert health["redis_ping"] == "success"
        assert "circuit_breaker" in health

        # Test unhealthy state
        connected_pubsub._connected = False
        health = await connected_pubsub.health_check()
        assert health["redis_ping"] == "not_connected"

    async def test_health_check_with_redis_error(self, connected_pubsub: RedisPubSub) -> None:
        """Test health check when Redis ping fails."""
        connected_pubsub._redis.ping = AsyncMock(side_effect=RedisError("Redis down"))

        health = await connected_pubsub.health_check()
        assert "failed:" in health["redis_ping"]

    async def test_health_check_with_circuit_breaker_open(self, connected_pubsub: RedisPubSub) -> None:
        """Test health check when circuit breaker is open."""
        # Force circuit breaker open
        connected_pubsub._circuit_breaker._state = CircuitBreakerState.OPEN
        connected_pubsub._circuit_breaker._next_attempt_time = time.time() + 3600

        health = await connected_pubsub.health_check()
        assert health["circuit_breaker"]["state"] == "open"

    async def test_properties_edge_cases(self, connected_pubsub: RedisPubSub) -> None:
        """Test property edge cases."""
        # Test active_subscriptions returns copy
        connected_pubsub._subscribers.add("test1")
        connected_pubsub._subscribers.add("test2")

        subscriptions = connected_pubsub.active_subscriptions
        subscriptions.add("test3")

        # Original should be unchanged
        assert "test3" not in connected_pubsub._subscribers
        assert len(connected_pubsub._subscribers) == 2

    async def test_disconnect_partial_cleanup_scenarios(self, connected_pubsub: RedisPubSub) -> None:
        """Test disconnect with partial cleanup scenarios."""
        # Setup various components with proper async mock
        mock_task = AsyncMock()
        mock_task.done.return_value = False
        mock_task.cancel = MagicMock()
        connected_pubsub._listening_task = mock_task

        # Mock components that might fail during cleanup
        connected_pubsub._pubsub = AsyncMock()
        # Make aclose fail to test error handling
        connected_pubsub._pubsub.aclose.side_effect = Exception("Cleanup error")

        connected_pubsub._redis = AsyncMock()
        connected_pubsub._pool = AsyncMock()

        # Should handle cleanup errors gracefully without raising
        await connected_pubsub.disconnect()

        assert not connected_pubsub._connected

    @pytest.mark.benchmark
    async def test_publish_performance_benchmark(self, connected_pubsub: RedisPubSub) -> None:
        """Test publish performance meets requirements."""
        connected_pubsub._redis.publish = AsyncMock(return_value=1)

        message = {"test": "data", "timestamp": time.time()}

        # Measure publish performance
        times = []
        for _ in range(20):  # Reduced from 100 iterations
            start = time.perf_counter()
            await connected_pubsub.publish("benchmark", message)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        # CI-aware threshold for mock Redis
        max_latency = 500.0 if os.getenv("CI") == "true" else 1.0
        assert avg_time < max_latency, f"Average publish time {avg_time:.3f}ms exceeds {max_latency}ms target"


class TestGlobalPubSubFunctions:
    """Test global pub/sub functions with comprehensive scenarios."""

    async def test_get_pubsub_singleton_behavior(self, monkeypatch: Any) -> None:
        """Test get_pubsub singleton behavior in various scenarios."""
        # Clear any existing instance
        await cleanup_pubsub()

        with patch("src.common.pubsub.RedisPubSub") as mock_cls, patch("src.common.pubsub._REDIS_AVAILABLE", True):
            mock_instance = AsyncMock()
            mock_instance.connect = AsyncMock()
            mock_cls.return_value = mock_instance

            # First call creates instance
            pubsub1 = await get_pubsub()
            assert mock_cls.call_count == 1
            assert mock_instance.connect.call_count == 1

            # Second call returns same instance
            pubsub2 = await get_pubsub()
            assert pubsub1 is pubsub2
            assert mock_cls.call_count == 1  # No new instance
            assert mock_instance.connect.call_count == 1  # No additional connect

    async def test_get_pubsub_connection_failure(self, monkeypatch: Any) -> None:
        """Test get_pubsub when connection fails."""
        await cleanup_pubsub()

        with patch("src.common.pubsub.RedisPubSub") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.connect.side_effect = Exception("Connection failed")
            mock_cls.return_value = mock_instance

            with pytest.raises(Exception, match="Connection failed"):
                await get_pubsub()

    async def test_cleanup_pubsub_edge_cases(self) -> None:
        """Test cleanup_pubsub edge cases."""
        # Test multiple cleanups
        await cleanup_pubsub()
        await cleanup_pubsub()  # Should not error

        # Test cleanup with mock instance
        with patch("src.common.pubsub.RedisPubSub") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.connect = AsyncMock()
            mock_instance.disconnect = AsyncMock()
            mock_cls.return_value = mock_instance

            # Create instance
            await get_pubsub()

            # Cleanup
            await cleanup_pubsub()
            mock_instance.disconnect.assert_called_once()

            # Next get_pubsub should create new instance
            await get_pubsub()
            assert mock_cls.call_count == 2

    async def test_cleanup_pubsub_with_disconnect_error(self) -> None:
        """Test cleanup when disconnect raises error."""
        await cleanup_pubsub()

        with patch("src.common.pubsub.RedisPubSub") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.connect = AsyncMock()
            # Make disconnect fail
            mock_instance.disconnect = AsyncMock(side_effect=Exception("Disconnect failed"))
            mock_cls.return_value = mock_instance

            # Create instance
            await get_pubsub()

            # Cleanup should handle error gracefully and not raise
            await cleanup_pubsub()  # Should not raise exception


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with pub/sub operations."""

    @pytest.fixture
    async def pubsub(self, mock_redis_config: Any, monkeypatch: Any) -> RedisPubSub:
        """Create RedisPubSub instance with mocked dependencies for circuit breaker tests."""
        monkeypatch.setattr("src.common.pubsub._REDIS_AVAILABLE", True)
        # Disable health monitor for unit tests to avoid 2-second delay
        monkeypatch.setattr("src.common.pubsub._HEALTH_MONITOR_AVAILABLE", False)
        monkeypatch.setattr("src.common.pubsub.get_redis_config", lambda: mock_redis_config)
        return RedisPubSub()

    async def test_circuit_breaker_protects_all_operations(self, pubsub: RedisPubSub, fake_redis: Any) -> None:
        """Test that circuit breaker protects all Redis operations."""
        pubsub._redis = fake_redis
        pubsub._connected = True

        # Force circuit breaker open
        pubsub._circuit_breaker._state = CircuitBreakerState.OPEN
        pubsub._circuit_breaker._next_attempt_time = time.time() + 3600

        # All operations should be blocked
        with pytest.raises(PublishError, match="blocked by circuit breaker"):
            await pubsub.publish("test", {"data": "test"})

        # get_subscribers_count should return 0 without error
        count = await pubsub.get_subscribers_count("test")
        assert count == 0

    @freeze_time("2023-01-01 00:00:00")
    async def test_circuit_breaker_recovery_scenarios(self, pubsub: RedisPubSub, fake_redis: Any) -> None:
        """Test circuit breaker recovery scenarios."""
        pubsub._redis = fake_redis
        pubsub._connected = True

        # Trigger circuit breaker opening
        fake_redis.publish = AsyncMock(side_effect=RedisError("Redis error"))

        # Cause exactly 3 failures to trigger circuit breaker (failure_threshold=3)
        for _ in range(3):
            with contextlib.suppress(PublishError):
                await pubsub.publish("test", {"data": "test"})

        # Verify circuit breaker opened
        assert pubsub.circuit_breaker_state == CircuitBreakerState.OPEN

        # Move time forward past the recovery timeout (30s + some buffer for jitter)
        # With 3 failures, backoff multiplier = min(2^(3-3), 8) = 1, so timeout = 30s
        with freeze_time("2023-01-01 00:00:35"):  # Move forward 35s to account for jitter
            fake_redis.publish = AsyncMock(return_value=1)

            # Should recover through HALF_OPEN to CLOSED
            result = await pubsub.publish("test", {"data": "test"})
            assert result == 1

            # Second success should close circuit (success_threshold=2)
            await pubsub.publish("test", {"data": "test"})
            assert pubsub.circuit_breaker_state == CircuitBreakerState.CLOSED  # type: ignore[comparison-overlap]
