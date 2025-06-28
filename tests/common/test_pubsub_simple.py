# Test file - configured per-file ignores in ruff.toml handle common test patterns
"""Simplified test suite for Redis Pub/Sub wrapper focused on core functionality."""

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

# Import pytest and Redis with graceful degradation - use Any for type hints to avoid linter issues
if TYPE_CHECKING:
    # These imports are only for type checking and won't be resolved by linter
    pass

# Import pytest and Redis with runtime checks
try:
    import pytest
    from redis.exceptions import ConnectionError as RedisConnectionError
    from redis.exceptions import RedisError

    _PYTEST_AVAILABLE = True
    _REDIS_AVAILABLE = True
except ImportError:
    # pytest and/or Redis not available in test environment
    pytest = None
    RedisConnectionError = Exception
    RedisError = Exception
    _PYTEST_AVAILABLE = False
    _REDIS_AVAILABLE = False

from src.common.pubsub import (
    MessageData,
    PublishError,
    PubSubError,
    RedisPubSub,
    SubscribeError,
    cleanup_pubsub,
    get_pubsub,
)


class TestRedisPubSubCore:
    """Core functionality tests for RedisPubSub."""

    def test_init(self) -> None:
        """Test RedisPubSub initialization."""
        if not _PYTEST_AVAILABLE:
            return

        pubsub = RedisPubSub()
        assert pubsub._pool is None
        assert pubsub._redis is None
        assert pubsub._pubsub is None
        assert pubsub._subscribers == set()
        assert pubsub._handlers == {}
        assert pubsub._listening_task is None
        assert not pubsub._connected

    @patch("src.common.pubsub.ConnectionPool")
    @patch("src.common.pubsub.aioredis.Redis")
    async def test_connect_success(self, mock_redis_cls: MagicMock, mock_pool_cls: MagicMock) -> None:
        """Test successful Redis connection."""
        if not _PYTEST_AVAILABLE:
            return

        # Setup mocks
        mock_pool = AsyncMock()
        mock_pool_cls.from_url.return_value = mock_pool

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis_cls.return_value = mock_redis

        pubsub = RedisPubSub()
        await pubsub.connect()

        # Verify connection setup
        assert pubsub._connected
        assert pubsub._pool == mock_pool
        assert pubsub._redis == mock_redis
        mock_redis.ping.assert_called_once()

    @patch("src.common.pubsub.ConnectionPool")
    async def test_connect_failure(self, mock_pool_cls: MagicMock) -> None:
        """Test Redis connection failure."""
        if not _PYTEST_AVAILABLE or not pytest:
            return

        mock_pool_cls.from_url.side_effect = RedisConnectionError("Connection failed")

        pubsub = RedisPubSub()
        with pytest.raises(PubSubError, match="Redis connection failed"):
            await pubsub.connect()

        assert not pubsub._connected

    async def test_disconnect_not_connected(self) -> None:
        """Test disconnect when not connected."""
        if not _PYTEST_AVAILABLE:
            return

        pubsub = RedisPubSub()
        await pubsub.disconnect()  # Should not raise exception

    async def test_publish_not_connected_auto_connect(self) -> None:
        """Test publishing when not connected triggers auto-connect."""
        if not _PYTEST_AVAILABLE:
            return

        pubsub = RedisPubSub()

        with patch.object(pubsub, "connect") as mock_connect:
            # Simulate connect() setting up the connection
            async def setup_connection() -> None:
                pubsub._connected = True
                mock_redis = AsyncMock()
                mock_redis.publish.return_value = 1
                pubsub._redis = mock_redis

            mock_connect.side_effect = setup_connection

            result = await pubsub.publish("test", {"data": "test"})

            mock_connect.assert_called_once()
            assert result == 1

    async def test_publish_redis_error(self) -> None:
        """Test publish with Redis error."""
        if not _PYTEST_AVAILABLE or not pytest:
            return

        pubsub = RedisPubSub()
        pubsub._connected = True

        mock_redis = AsyncMock()
        mock_redis.publish.side_effect = RedisError("Redis error")
        pubsub._redis = mock_redis

        with pytest.raises(PublishError, match="Failed to publish message"):
            await pubsub.publish("test", {"data": "test"})

    async def test_publish_json_error(self) -> None:
        """Test publish with JSON serialization error."""
        if not _PYTEST_AVAILABLE or not pytest:
            return

        pubsub = RedisPubSub()
        pubsub._connected = True

        mock_redis = AsyncMock()
        pubsub._redis = mock_redis

        # Create non-serializable object
        class NonSerializable:
            pass

        with pytest.raises(PublishError, match="Failed to publish message"):
            await pubsub.publish("test", {"obj": NonSerializable()})

    async def test_subscribe_not_connected_auto_connect(self) -> None:
        """Test subscribing when not connected triggers auto-connect."""
        if not _PYTEST_AVAILABLE:
            return

        pubsub = RedisPubSub()

        async def handler(channel: str, message: MessageData) -> None:
            pass

        with patch.object(pubsub, "connect") as mock_connect:
            # Simulate connect() setting up the connection
            async def setup_connection() -> None:
                pubsub._connected = True
                mock_pubsub = AsyncMock()
                mock_pubsub.subscribe = AsyncMock()
                mock_redis = AsyncMock()
                mock_redis.pubsub.return_value = mock_pubsub
                pubsub._redis = mock_redis
                pubsub._pubsub = mock_pubsub

            mock_connect.side_effect = setup_connection

            await pubsub.subscribe("test", handler)
            mock_connect.assert_called_once()

    async def test_unsubscribe_nonexistent_channel(self) -> None:
        """Test unsubscribing from nonexistent channel."""
        if not _PYTEST_AVAILABLE:
            return

        pubsub = RedisPubSub()

        async def handler(channel: str, message: MessageData) -> None:
            pass

        # Should not raise exception
        await pubsub.unsubscribe("nonexistent", handler)

    async def test_handle_message_success(self) -> None:
        """Test successful message handling."""
        if not _PYTEST_AVAILABLE:
            return

        pubsub = RedisPubSub()
        received_messages = []

        async def handler(channel: str, message: MessageData) -> None:
            received_messages.append((channel, message))

        pubsub._handlers["test_channel"] = [handler]

        # Test with bytes data
        message = {"type": "message", "channel": b"test_channel", "data": b'{"test": "data", "number": 42}'}

        await pubsub._handle_message(message)

        assert len(received_messages) == 1
        assert received_messages[0] == ("test_channel", {"test": "data", "number": 42})

    async def test_handle_message_no_handlers(self) -> None:
        """Test handling message with no registered handlers."""
        if not _PYTEST_AVAILABLE:
            return

        pubsub = RedisPubSub()

        message = {"type": "message", "channel": "unknown_channel", "data": '{"test": "data"}'}

        # Should not raise exception
        await pubsub._handle_message(message)

    async def test_handle_message_json_decode_error(self, caplog: Any) -> None:
        """Test handling message with invalid JSON."""
        if not _PYTEST_AVAILABLE:
            return

        pubsub = RedisPubSub()

        async def handler(channel: str, message: MessageData) -> None:
            pass

        pubsub._handlers["test_channel"] = [handler]

        message = {"type": "message", "channel": "test_channel", "data": b"invalid json"}

        await pubsub._handle_message(message)

        assert "Failed to decode message" in caplog.text

    async def test_get_subscribers_count_not_connected(self) -> None:
        """Test getting subscriber count when not connected."""
        if not _PYTEST_AVAILABLE:
            return

        pubsub = RedisPubSub()

        with patch.object(pubsub, "connect") as mock_connect:
            # Simulate connect() setting up the connection
            async def setup_connection() -> None:
                pubsub._connected = True
                mock_redis = AsyncMock()
                mock_redis.pubsub_numsub.return_value = {"test": 3}
                pubsub._redis = mock_redis

            mock_connect.side_effect = setup_connection

            count = await pubsub.get_subscribers_count("test")

            mock_connect.assert_called_once()
            assert count == 3

    async def test_get_subscribers_count_redis_error(self, caplog: Any) -> None:
        """Test getting subscriber count with Redis error."""
        if not _PYTEST_AVAILABLE:
            return

        pubsub = RedisPubSub()
        pubsub._connected = True

        mock_redis = AsyncMock()
        mock_redis.pubsub_numsub.side_effect = RedisError("Redis error")
        pubsub._redis = mock_redis

        count = await pubsub.get_subscribers_count("test")

        assert count == 0
        assert "Failed to get subscriber count" in caplog.text

    def test_is_connected_property(self) -> None:
        """Test is_connected property."""
        if not _PYTEST_AVAILABLE:
            return

        pubsub = RedisPubSub()
        assert not pubsub.is_connected
        pubsub._connected = True
        assert pubsub.is_connected

    def test_active_subscriptions_property(self) -> None:
        """Test active_subscriptions property."""
        if not _PYTEST_AVAILABLE:
            return

        pubsub = RedisPubSub()
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
        if not _PYTEST_AVAILABLE:
            return

        # Clear global instance first
        await cleanup_pubsub()

        with (
            patch("src.common.pubsub.RedisPubSub") as mock_cls,
            patch("src.common.pubsub.ConnectionPool"),
            patch("src.common.pubsub.aioredis.Redis"),
        ):
            mock_instance = AsyncMock()
            mock_instance.connect = AsyncMock()
            mock_cls.return_value = mock_instance

            pubsub1 = await get_pubsub()
            pubsub2 = await get_pubsub()

            assert pubsub1 is pubsub2
            mock_cls.assert_called_once()
            mock_instance.connect.assert_called_once()

    async def test_cleanup_pubsub_no_instance(self) -> None:
        """Test cleanup_pubsub when no instance exists."""
        if not _PYTEST_AVAILABLE:
            return

        # Clear any existing instance
        await cleanup_pubsub()
        # Should not raise exception
        await cleanup_pubsub()


class TestErrorClasses:
    """Test suite for custom exception classes."""

    def test_pubsub_error(self) -> None:
        """Test PubSubError exception."""
        if not _PYTEST_AVAILABLE:
            return

        error = PubSubError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_publish_error(self) -> None:
        """Test PublishError exception."""
        if not _PYTEST_AVAILABLE:
            return

        error = PublishError("Publish failed")
        assert str(error) == "Publish failed"
        assert isinstance(error, PubSubError)

    def test_subscribe_error(self) -> None:
        """Test SubscribeError exception."""
        if not _PYTEST_AVAILABLE:
            return

        error = SubscribeError("Subscribe failed")
        assert str(error) == "Subscribe failed"
        assert isinstance(error, PubSubError)


# Only define integration tests if pytest is available
if _PYTEST_AVAILABLE and pytest:

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
            except Exception:
                # Skip integration tests if Redis not available
                pytest.skip("Redis not available for integration tests")
            finally:
                with contextlib.suppress(Exception):
                    await pubsub.disconnect()

        @pytest.mark.slow
        async def test_basic_pubsub_functionality(self, live_pubsub: RedisPubSub) -> None:
            """Test basic pub/sub functionality with real Redis."""
            received_messages = []

            async def message_handler(channel: str, message: MessageData) -> None:
                received_messages.append((channel, message))

            # Subscribe to channel
            await live_pubsub.subscribe("test_basic", message_handler)

            # Give subscription time to establish
            await asyncio.sleep(0.1)

            # Test message data
            test_message = {"test": "basic", "number": 42}

            # Publish message
            subscriber_count = await live_pubsub.publish("test_basic", test_message)

            # Wait for message processing
            await asyncio.sleep(0.1)

            # Verify results
            assert subscriber_count >= 1
            assert len(received_messages) == 1
            assert received_messages[0][0] == "test_basic"
            assert received_messages[0][1] == test_message
