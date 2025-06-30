"""Comprehensive test suite for Redis Pub/Sub wrapper.

Tests cover all functionality with focus on performance, error handling,
and edge cases to achieve 95%+ code coverage.
"""

import asyncio
import builtins
import contextlib
import time
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from src.common.pubsub import (
    MessageData,
    PublishError,
    PubSubError,
    RedisPubSub,
    SubscribeError,
    cleanup_pubsub,
    get_pubsub,
)


class TestRedisPubSub:
    """Test suite for RedisPubSub class."""

    @pytest.fixture
    async def pubsub(self) -> RedisPubSub:
        """Create RedisPubSub instance for testing."""
        return RedisPubSub()

    @pytest.fixture
    async def connected_pubsub(self, pubsub: RedisPubSub) -> AsyncGenerator[RedisPubSub, None]:
        """Create connected RedisPubSub instance."""
        with (
            patch("src.common.pubsub.ConnectionPool") as mock_pool_cls,
            patch("src.common.pubsub.redis.Redis") as mock_redis_cls,
        ):
            # Create mock pool with async aclose method
            mock_pool = AsyncMock()
            mock_pool.aclose = AsyncMock()
            mock_pool_cls.from_url.return_value = mock_pool

            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis.aclose = AsyncMock()
            mock_redis_cls.return_value = mock_redis

            await pubsub.connect()
            yield pubsub
            await pubsub.disconnect()

    async def test_init(self, pubsub: RedisPubSub) -> None:
        """Test RedisPubSub initialization."""
        assert pubsub._pool is None
        assert pubsub._redis is None
        assert pubsub._pubsub is None
        assert pubsub._subscribers == set()
        assert pubsub._handlers == {}
        assert pubsub._listening_task is None
        assert not pubsub._connected

    @patch("src.common.pubsub.ConnectionPool", new_callable=AsyncMock)
    @patch("src.common.pubsub.redis.Redis")
    async def test_connect_success(
        self,
        mock_redis_cls: MagicMock,
        mock_pool_cls: AsyncMock,
        pubsub: RedisPubSub,
    ) -> None:
        """Test successful Redis connection."""
        # Setup mocks
        mock_pool = AsyncMock()
        mock_pool_cls.from_url.return_value = mock_pool

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis_cls.return_value = mock_redis

        # Test connection
        await pubsub.connect()

        # Verify connection setup
        assert pubsub._connected
        assert pubsub._pool == mock_pool
        assert pubsub._redis == mock_redis
        mock_redis.ping.assert_called_once()

    @patch("src.common.pubsub.ConnectionPool", new_callable=AsyncMock)
    async def test_connect_failure(self, mock_pool_cls: AsyncMock, pubsub: RedisPubSub) -> None:
        """Test Redis connection failure."""
        mock_pool_cls.from_url.side_effect = RedisConnectionError("Connection failed")

        with pytest.raises(PubSubError, match="Redis connection failed"):
            await pubsub.connect()

        assert not pubsub._connected

    async def test_connect_already_connected(self, connected_pubsub: RedisPubSub) -> None:
        """Test connecting when already connected."""
        # Mock the ping method to ensure it's awaitable
        connected_pubsub._redis.ping = AsyncMock()

        # Should not raise exception or change state
        await connected_pubsub.connect()
        assert connected_pubsub._connected

    async def test_disconnect_success(self, connected_pubsub: RedisPubSub) -> None:
        """Test successful disconnection."""
        # Add mock components
        connected_pubsub._listening_task = AsyncMock()
        connected_pubsub._listening_task.done.return_value = False
        connected_pubsub._listening_task.cancel = AsyncMock()

        connected_pubsub._pubsub = AsyncMock()
        connected_pubsub._pubsub.aclose = AsyncMock()

        connected_pubsub._redis = AsyncMock()
        connected_pubsub._redis.aclose = AsyncMock()

        connected_pubsub._pool = AsyncMock()
        connected_pubsub._pool.aclose = AsyncMock()

        await connected_pubsub.disconnect()

        # Verify cleanup
        assert not connected_pubsub._connected
        assert connected_pubsub._subscribers == set()
        assert connected_pubsub._handlers == {}

    async def test_disconnect_not_connected(self, pubsub: RedisPubSub) -> None:
        """Test disconnect when not connected."""
        await pubsub.disconnect()  # Should not raise exception

    async def test_publish_success(self, connected_pubsub: RedisPubSub) -> None:
        """Test successful message publishing."""
        # Setup mock
        mock_redis = AsyncMock()
        mock_redis.publish.return_value = 2
        connected_pubsub._redis = mock_redis

        message = {"test": "data", "number": 42}
        result = await connected_pubsub.publish("test_channel", message)

        assert result == 2
        mock_redis.publish.assert_called_once_with("test_channel", '{"test":"data","number":42}')

    async def test_publish_not_connected(self, pubsub: RedisPubSub) -> None:
        """Test publishing when not connected (should auto-connect)."""
        with patch.object(pubsub, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None
            pubsub._connected = True
            mock_redis = AsyncMock()
            mock_redis.publish.return_value = 1
            pubsub._redis = mock_redis

            result = await pubsub.publish("test", {"data": "test"})

            mock_connect.assert_called_once()
            assert result == 1

    async def test_publish_redis_error(self, connected_pubsub: RedisPubSub) -> None:
        """Test publish with Redis error."""
        mock_redis = AsyncMock()
        mock_redis.publish.side_effect = RedisError("Redis error")
        connected_pubsub._redis = mock_redis

        with pytest.raises(PublishError, match="Failed to publish message"):
            await connected_pubsub.publish("test", {"data": "test"})

    async def test_publish_json_error(self, connected_pubsub: RedisPubSub) -> None:
        """Test publish with JSON serialization error."""
        mock_redis = AsyncMock()
        connected_pubsub._redis = mock_redis

        # Create non-serializable object
        class NonSerializable:
            pass

        with pytest.raises(PublishError, match="Failed to publish message"):
            await connected_pubsub.publish("test", {"obj": NonSerializable()})

    async def test_publish_performance_warning(self, connected_pubsub: RedisPubSub, caplog: Any) -> None:
        """Test publish performance warning for slow operations."""
        mock_redis = AsyncMock()

        # Mock slow publish operation
        async def slow_publish(*args: Any, **kwargs: Any) -> int:
            await asyncio.sleep(0.002)  # 2ms delay
            return 1

        mock_redis.publish = slow_publish
        connected_pubsub._redis = mock_redis

        await connected_pubsub.publish("test", {"data": "test"})

        # Check for performance warning
        assert "exceeded 1ms target" in caplog.text

    async def test_subscribe_success(self, connected_pubsub: RedisPubSub) -> None:
        """Test successful channel subscription."""
        # Setup mocks
        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        connected_pubsub._redis = mock_redis

        async def test_handler(channel: str, message: MessageData) -> None:
            pass

        await connected_pubsub.subscribe("test_channel", test_handler)

        # Verify subscription
        assert "test_channel" in connected_pubsub._subscribers
        assert "test_channel" in connected_pubsub._handlers
        assert test_handler in connected_pubsub._handlers["test_channel"]
        mock_pubsub.subscribe.assert_called_once_with("test_channel")

    async def test_subscribe_multiple_handlers(self, connected_pubsub: RedisPubSub) -> None:
        """Test subscribing multiple handlers to same channel."""
        mock_pubsub = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        connected_pubsub._redis = mock_redis

        async def handler1(channel: str, message: MessageData) -> None:
            pass

        async def handler2(channel: str, message: MessageData) -> None:
            pass

        await connected_pubsub.subscribe("test_channel", handler1)
        await connected_pubsub.subscribe("test_channel", handler2)

        # Should only subscribe to channel once
        assert len(connected_pubsub._handlers["test_channel"]) == 2
        mock_pubsub.subscribe.assert_called_once_with("test_channel")

    async def test_subscribe_not_connected(self, pubsub: RedisPubSub) -> None:
        """Test subscribing when not connected (should auto-connect)."""
        with patch.object(pubsub, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None
            pubsub._connected = True
            mock_pubsub = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.pubsub.return_value = mock_pubsub
            pubsub._redis = mock_redis

            async def handler(channel: str, message: MessageData) -> None:
                pass

            await pubsub.subscribe("test", handler)
            mock_connect.assert_called_once()

    async def test_subscribe_redis_error(self, connected_pubsub: RedisPubSub) -> None:
        """Test subscription with Redis error."""
        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe.side_effect = RedisError("Redis error")
        mock_redis = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        connected_pubsub._redis = mock_redis

        async def handler(channel: str, message: MessageData) -> None:
            pass

        with pytest.raises(SubscribeError, match="Failed to subscribe"):
            await connected_pubsub.subscribe("test", handler)

    async def test_unsubscribe_specific_handler(self, connected_pubsub: RedisPubSub) -> None:
        """Test unsubscribing specific handler."""
        # Setup initial subscription
        mock_pubsub = AsyncMock()
        connected_pubsub._pubsub = mock_pubsub
        connected_pubsub._subscribers.add("test_channel")

        async def handler1(channel: str, message: MessageData) -> None:
            pass

        async def handler2(channel: str, message: MessageData) -> None:
            pass

        connected_pubsub._handlers["test_channel"] = [handler1, handler2]

        # Unsubscribe one handler
        await connected_pubsub.unsubscribe("test_channel", handler1)

        # Should remove handler but keep subscription
        assert handler1 not in connected_pubsub._handlers["test_channel"]
        assert handler2 in connected_pubsub._handlers["test_channel"]
        assert "test_channel" in connected_pubsub._subscribers
        mock_pubsub.unsubscribe.assert_not_called()

    async def test_unsubscribe_all_handlers(self, connected_pubsub: RedisPubSub) -> None:
        """Test unsubscribing all handlers from channel."""
        mock_pubsub = AsyncMock()
        connected_pubsub._pubsub = mock_pubsub
        connected_pubsub._subscribers.add("test_channel")

        async def handler(channel: str, message: MessageData) -> None:
            pass

        connected_pubsub._handlers["test_channel"] = [handler]

        # Unsubscribe all handlers
        await connected_pubsub.unsubscribe("test_channel")

        # Should remove channel entirely
        assert "test_channel" not in connected_pubsub._handlers
        assert "test_channel" not in connected_pubsub._subscribers
        mock_pubsub.unsubscribe.assert_called_once_with("test_channel")

    async def test_unsubscribe_last_handler(self, connected_pubsub: RedisPubSub) -> None:
        """Test unsubscribing the last handler from channel."""
        mock_pubsub = AsyncMock()
        connected_pubsub._pubsub = mock_pubsub
        connected_pubsub._subscribers.add("test_channel")

        async def handler(channel: str, message: MessageData) -> None:
            pass

        connected_pubsub._handlers["test_channel"] = [handler]

        # Unsubscribe last handler
        await connected_pubsub.unsubscribe("test_channel", handler)

        # Should unsubscribe from channel
        assert "test_channel" not in connected_pubsub._handlers
        assert "test_channel" not in connected_pubsub._subscribers
        mock_pubsub.unsubscribe.assert_called_once_with("test_channel")

    async def test_unsubscribe_nonexistent_channel(self, connected_pubsub: RedisPubSub) -> None:
        """Test unsubscribing from nonexistent channel."""

        async def handler(channel: str, message: MessageData) -> None:
            pass

        # Should not raise exception
        await connected_pubsub.unsubscribe("nonexistent", handler)

    async def test_unsubscribe_redis_error(self, connected_pubsub: RedisPubSub) -> None:
        """Test unsubscription with Redis error."""
        mock_pubsub = AsyncMock()
        mock_pubsub.unsubscribe.side_effect = RedisError("Redis error")
        connected_pubsub._pubsub = mock_pubsub
        connected_pubsub._subscribers.add("test_channel")
        connected_pubsub._handlers["test_channel"] = []

        with pytest.raises(SubscribeError, match="Failed to unsubscribe"):
            await connected_pubsub.unsubscribe("test_channel")

    async def test_handle_message_success(self, connected_pubsub: RedisPubSub) -> None:
        """Test successful message handling."""
        received_messages = []

        async def handler(channel: str, message: MessageData) -> None:
            received_messages.append((channel, message))

        connected_pubsub._handlers["test_channel"] = [handler]

        # Test with bytes data
        message = {"type": "message", "channel": b"test_channel", "data": b'{"test": "data", "number": 42}'}

        await connected_pubsub._handle_message(message)

        assert len(received_messages) == 1
        assert received_messages[0] == ("test_channel", {"test": "data", "number": 42})

    async def test_handle_message_string_channel(self, connected_pubsub: RedisPubSub) -> None:
        """Test message handling with string channel."""
        received_messages = []

        async def handler(channel: str, message: MessageData) -> None:
            received_messages.append((channel, message))

        connected_pubsub._handlers["test_channel"] = [handler]

        message = {"type": "message", "channel": "test_channel", "data": '{"test": "data"}'}

        await connected_pubsub._handle_message(message)

        assert len(received_messages) == 1
        assert received_messages[0] == ("test_channel", {"test": "data"})

    async def test_handle_message_no_handlers(self, connected_pubsub: RedisPubSub) -> None:
        """Test handling message with no registered handlers."""
        message = {"type": "message", "channel": "unknown_channel", "data": '{"test": "data"}'}

        # Should not raise exception
        await connected_pubsub._handle_message(message)

    async def test_handle_message_json_decode_error(self, connected_pubsub: RedisPubSub, caplog: Any) -> None:
        """Test handling message with invalid JSON."""

        async def handler(channel: str, message: MessageData) -> None:
            pass

        connected_pubsub._handlers["test_channel"] = [handler]

        message = {"type": "message", "channel": "test_channel", "data": b"invalid json"}

        await connected_pubsub._handle_message(message)

        assert "Failed to decode message" in caplog.text

    async def test_handle_message_handler_exception(self, connected_pubsub: RedisPubSub, caplog: Any) -> None:
        """Test handling message when handler raises exception."""

        async def failing_handler(channel: str, message: MessageData) -> None:
            raise ValueError("Handler error")

        connected_pubsub._handlers["test_channel"] = [failing_handler]

        message = {"type": "message", "channel": "test_channel", "data": '{"test": "data"}'}

        await connected_pubsub._handle_message(message)

        assert "Error handling message" in caplog.text

    async def test_listen_loop_message_processing(self, connected_pubsub: RedisPubSub) -> None:
        """Test listen loop processes messages correctly."""
        messages = [
            {"type": "subscribe", "channel": "test", "data": 1},
            {"type": "message", "channel": "test", "data": '{"test": "data"}'},
            {"type": "unsubscribe", "channel": "test", "data": 0},
        ]

        async def mock_listen() -> AsyncGenerator[dict[str, Any], None]:
            for msg in messages:
                yield msg  # type: ignore[misc]

        mock_pubsub = AsyncMock()
        mock_pubsub.listen = AsyncMock(return_value=mock_listen())
        connected_pubsub._pubsub = mock_pubsub

        received_messages = []

        async def handler(channel: str, message: MessageData) -> None:
            received_messages.append((channel, message))

        connected_pubsub._handlers["test"] = [handler]

        # Run listen loop with timeout to prevent hanging
        with contextlib.suppress(builtins.TimeoutError):
            await asyncio.wait_for(connected_pubsub._listen_loop(), timeout=0.1)

        assert len(received_messages) == 1
        assert received_messages[0] == ("test", {"test": "data"})

    async def test_listen_loop_redis_error_reconnect(self, connected_pubsub: RedisPubSub) -> None:
        """Test listen loop handles Redis errors with reconnection."""

        async def mock_listen() -> AsyncGenerator[dict[str, Any], None]:
            raise RedisError("Connection lost")
            yield  # pragma: no cover

        mock_pubsub = AsyncMock()
        mock_pubsub.listen = AsyncMock(return_value=mock_listen())
        mock_pubsub.subscribe = AsyncMock()
        connected_pubsub._pubsub = mock_pubsub
        connected_pubsub._subscribers.add("test_channel")

        with patch.object(connected_pubsub, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None

            # Should handle error without crashing
            with contextlib.suppress(builtins.TimeoutError):
                await asyncio.wait_for(connected_pubsub._listen_loop(), timeout=0.1)

            mock_connect.assert_called_once()

    async def test_listen_loop_cancelled(self, connected_pubsub: RedisPubSub) -> None:
        """Test listen loop handles cancellation gracefully."""

        async def mock_listen() -> AsyncGenerator[dict[str, Any], None]:
            await asyncio.sleep(1)  # Simulate long operation
            yield {"type": "message", "channel": "test", "data": "{}"}  # pragma: no cover

        mock_pubsub = AsyncMock()
        mock_pubsub.listen = AsyncMock(return_value=mock_listen())
        connected_pubsub._pubsub = mock_pubsub

        task = asyncio.create_task(connected_pubsub._listen_loop())
        await asyncio.sleep(0.01)  # Let task start
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_channel_subscription_context_manager(self, connected_pubsub: RedisPubSub) -> None:
        """Test channel subscription context manager."""
        mock_pubsub = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        connected_pubsub._redis = mock_redis

        received_messages = []

        async def handler(channel: str, message: MessageData) -> None:
            received_messages.append((channel, message))

        # Test context manager
        async with connected_pubsub.channel_subscription("test_channel") as add_handler:
            await add_handler(handler)
            assert "test_channel" in connected_pubsub._subscribers
            assert handler in connected_pubsub._handlers["test_channel"]

        # Should auto-unsubscribe when exiting context
        assert "test_channel" not in connected_pubsub._subscribers
        assert "test_channel" not in connected_pubsub._handlers

    async def test_get_subscribers_count_success(self, connected_pubsub: RedisPubSub) -> None:
        """Test getting subscriber count for channel."""
        mock_redis = AsyncMock()
        mock_redis.pubsub_numsub.return_value = {"test_channel": 5}
        connected_pubsub._redis = mock_redis

        count = await connected_pubsub.get_subscribers_count("test_channel")

        assert count == 5
        mock_redis.pubsub_numsub.assert_called_once_with("test_channel")

    async def test_get_subscribers_count_not_connected(self, pubsub: RedisPubSub) -> None:
        """Test getting subscriber count when not connected."""
        with patch.object(pubsub, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None
            pubsub._connected = True
            mock_redis = AsyncMock()
            mock_redis.pubsub_numsub.return_value = {"test": 3}
            pubsub._redis = mock_redis

            count = await pubsub.get_subscribers_count("test")

            mock_connect.assert_called_once()
            assert count == 3

    async def test_get_subscribers_count_channel_not_found(self, connected_pubsub: RedisPubSub) -> None:
        """Test getting subscriber count for nonexistent channel."""
        mock_redis = AsyncMock()
        mock_redis.pubsub_numsub.return_value = {}
        connected_pubsub._redis = mock_redis

        count = await connected_pubsub.get_subscribers_count("nonexistent")

        assert count == 0

    async def test_get_subscribers_count_redis_error(self, connected_pubsub: RedisPubSub, caplog: Any) -> None:
        """Test getting subscriber count with Redis error."""
        mock_redis = AsyncMock()
        mock_redis.pubsub_numsub.side_effect = RedisError("Redis error")
        connected_pubsub._redis = mock_redis

        count = await connected_pubsub.get_subscribers_count("test")

        assert count == 0
        assert "Failed to get subscriber count" in caplog.text

    def test_is_connected_property(self, pubsub: RedisPubSub) -> None:
        """Test is_connected property."""
        assert not pubsub.is_connected
        pubsub._connected = True
        assert pubsub.is_connected

    def test_active_subscriptions_property(self, pubsub: RedisPubSub) -> None:
        """Test active_subscriptions property."""
        assert pubsub.active_subscriptions == set()

        pubsub._subscribers.add("channel1")
        pubsub._subscribers.add("channel2")

        subscriptions = pubsub.active_subscriptions
        assert subscriptions == {"channel1", "channel2"}

        # Should return copy, not reference
        subscriptions.add("channel3")
        assert "channel3" not in pubsub._subscribers


class TestGlobalFunctions:
    """Test suite for global Pub/Sub functions."""

    async def test_get_pubsub_singleton(self) -> None:
        """Test get_pubsub returns singleton instance."""
        # Clear global instance first
        await cleanup_pubsub()

        with (
            patch("src.common.pubsub.RedisPubSub") as mock_cls,
            patch("src.common.pubsub.ConnectionPool", new_callable=AsyncMock),
            patch("src.common.pubsub.redis.Redis"),
        ):
            mock_instance = AsyncMock()
            mock_instance.connect = AsyncMock()
            mock_cls.return_value = mock_instance

            pubsub1 = await get_pubsub()
            pubsub2 = await get_pubsub()

            assert pubsub1 is pubsub2
            mock_cls.assert_called_once()
            mock_instance.connect.assert_called_once()

    async def test_cleanup_pubsub(self) -> None:
        """Test cleanup_pubsub cleans up singleton."""
        # Clear global instance first
        await cleanup_pubsub()

        with (
            patch("src.common.pubsub.RedisPubSub") as mock_cls,
            patch("src.common.pubsub.ConnectionPool", new_callable=AsyncMock),
            patch("src.common.pubsub.redis.Redis"),
        ):
            mock_instance = AsyncMock()
            mock_instance.connect = AsyncMock()
            mock_instance.disconnect = AsyncMock()
            mock_cls.return_value = mock_instance

            pubsub1 = await get_pubsub()

            # Clean up
            await cleanup_pubsub()

            mock_instance.disconnect.assert_called_once()

            # Next get_pubsub should create new instance
            pubsub2 = await get_pubsub()

            # Should be different instances and connect called twice total
            assert pubsub1 is not pubsub2
            assert mock_cls.call_count == 2
            assert mock_instance.connect.call_count == 2

    async def test_cleanup_pubsub_no_instance(self) -> None:
        """Test cleanup_pubsub when no instance exists."""
        # Should not raise exception
        await cleanup_pubsub()


class TestErrorClasses:
    """Test suite for custom exception classes."""

    def test_pubsub_error(self) -> None:
        """Test PubSubError exception."""
        error = PubSubError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_publish_error(self) -> None:
        """Test PublishError exception."""
        error = PublishError("Publish failed")
        assert str(error) == "Publish failed"
        assert isinstance(error, PubSubError)

    def test_subscribe_error(self) -> None:
        """Test SubscribeError exception."""
        error = SubscribeError("Subscribe failed")
        assert str(error) == "Subscribe failed"
        assert isinstance(error, PubSubError)


@pytest.mark.integration
class TestRedisPubSubIntegration:
    """Integration tests requiring actual Redis instance."""

    @pytest.fixture
    async def live_pubsub(self) -> AsyncGenerator[RedisPubSub, None]:
        """Create RedisPubSub with real Redis connection."""
        pubsub = RedisPubSub()
        try:
            await pubsub.connect()
            yield pubsub
        finally:
            await pubsub.disconnect()

    @pytest.mark.slow
    async def test_end_to_end_pubsub(self, live_pubsub: RedisPubSub) -> None:
        """Test complete pub/sub workflow with real Redis."""
        received_messages = []

        async def message_handler(channel: str, message: MessageData) -> None:
            received_messages.append((channel, message))

        # Subscribe to channel
        await live_pubsub.subscribe("integration_test", message_handler)

        # Give subscription time to establish
        await asyncio.sleep(0.1)

        # Test message data
        test_message = {"test": "integration", "timestamp": time.time(), "data": {"nested": "value", "number": 123}}

        # Publish message
        subscriber_count = await live_pubsub.publish("integration_test", test_message)

        # Wait for message processing
        await asyncio.sleep(0.1)

        # Verify results
        assert subscriber_count >= 1
        assert len(received_messages) == 1
        assert received_messages[0][0] == "integration_test"
        assert received_messages[0][1] == test_message

    @pytest.mark.slow
    async def test_performance_benchmark(self, live_pubsub: RedisPubSub) -> None:
        """Test publish performance meets <1ms target."""
        test_message = {"benchmark": "test", "data": "small_payload"}

        # Warm up connection
        await live_pubsub.publish("benchmark_warmup", test_message)

        # Measure multiple publishes
        times = []
        for _ in range(10):
            start = time.perf_counter()
            await live_pubsub.publish("benchmark_test", test_message)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        # Calculate statistics
        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Performance assertions (may need adjustment based on hardware)
        assert avg_time < 5.0, f"Average publish time {avg_time:.2f}ms exceeds 5ms threshold"
        assert max_time < 10.0, f"Max publish time {max_time:.2f}ms exceeds 10ms threshold"

        # At least 50% should be under 1ms target
        fast_publishes = sum(1 for t in times if t < 1.0)
        assert fast_publishes >= 5, f"Only {fast_publishes}/10 publishes met <1ms target"
