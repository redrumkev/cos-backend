# ruff: noqa: I001
"""High-performance Redis Pub/Sub wrapper for COS.

This module provides a lightweight, high-performance Redis Pub/Sub wrapper designed for
<1ms publish latency with comprehensive error handling and connection management.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

# Import Redis with graceful degradation - use Any for type hints to avoid linter issues
if TYPE_CHECKING:
    # These imports are only for type checking and won't be resolved by linter
    pass

logger = logging.getLogger(__name__)

# Import redis with runtime checks
try:
    import redis.asyncio as aioredis
    from redis.asyncio.connection import ConnectionPool
    from redis.exceptions import (
        ConnectionError as RedisConnectionError,
        RedisError,
        TimeoutError as RedisTimeoutError,
    )

    _REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis package not available. Pub/Sub functionality will be disabled.")
    aioredis = None
    ConnectionPool = None
    RedisConnectionError = Exception
    RedisError = Exception
    RedisTimeoutError = Exception
    _REDIS_AVAILABLE = False

from .redis_config import get_redis_config  # noqa: E402

# Type aliases for clarity
MessageHandler = Callable[[str, dict[str, Any]], Awaitable[None]]
MessageData = dict[str, Any]


class PubSubError(Exception):
    """Base exception for Pub/Sub operations."""


class PublishError(PubSubError):
    """Exception raised when message publishing fails."""


class SubscribeError(PubSubError):
    """Exception raised when subscription operations fail."""


class RedisPubSub:
    """High-performance Redis Pub/Sub wrapper with connection pooling.

    Designed for <1ms publish latency with automatic connection management,
    error handling, and JSON serialization/deserialization.
    """

    def __init__(self) -> None:
        """Initialize Redis Pub/Sub client with optimized connection pool."""
        if not _REDIS_AVAILABLE:
            raise PubSubError("Redis package is required for pub/sub functionality. Install with: pip install redis")

        self._config = get_redis_config()
        self._pool: Any = None  # Redis connection pool
        self._redis: Any = None  # Redis client instance
        self._pubsub: Any = None  # Redis PubSub instance
        self._subscribers: set[str] = set()
        self._handlers: dict[str, list[MessageHandler]] = {}
        self._listening_task: asyncio.Task[None] | None = None
        self._connected = False

    async def connect(self) -> None:
        """Establish Redis connection with optimized pool settings."""
        if self._connected:
            return

        if not _REDIS_AVAILABLE:
            raise PubSubError("Redis package is required for connection")

        try:
            # Create optimized connection pool
            assert ConnectionPool is not None, "Redis ConnectionPool not available"
            self._pool = ConnectionPool.from_url(
                self._config.redis_url,
                max_connections=self._config.redis_max_connections,
                socket_connect_timeout=self._config.redis_socket_connect_timeout,
                socket_keepalive=self._config.redis_socket_keepalive,
                retry_on_timeout=self._config.redis_retry_on_timeout,
                health_check_interval=self._config.redis_health_check_interval,
                # Performance optimizations
                socket_read_size=65536,  # Larger read buffer
                retry_on_error=[RedisConnectionError, RedisTimeoutError],
                retry=3,  # Quick retries for transient failures
            )

            assert aioredis is not None, "Redis aioredis not available"
            self._redis = aioredis.Redis(
                connection_pool=self._pool,
                decode_responses=False,  # Handle bytes for performance
            )

            # Test connection
            assert self._redis is not None  # mypy assertion
            await self._redis.ping()
            self._connected = True
            logger.info("Redis Pub/Sub connected successfully")

        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise PubSubError(f"Redis connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Gracefully disconnect from Redis."""
        if not self._connected:
            return

        try:
            # Stop listening task
            if self._listening_task and not self._listening_task.done():
                self._listening_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._listening_task

            # Close pubsub connection
            if self._pubsub:
                await self._pubsub.aclose()
                self._pubsub = None

            # Close Redis connection
            if self._redis:
                await self._redis.aclose()
                self._redis = None

            # Close connection pool
            if self._pool:
                await self._pool.aclose()
                self._pool = None

            self._connected = False
            self._subscribers.clear()
            self._handlers.clear()
            logger.info("Redis Pub/Sub disconnected")

        except RedisError as e:
            logger.error(f"Error during Redis disconnect: {e}")

    async def publish(self, channel: str, message: MessageData) -> int:
        """Publish message to Redis channel with <1ms latency target.

        Args:
        ----
            channel: Redis channel name
            message: Message data to publish (will be JSON serialized)

        Returns:
        -------
            Number of subscribers that received the message

        Raises:
        ------
            PublishError: If publishing fails

        """
        if not self._connected or not self._redis:
            await self.connect()

        assert self._redis is not None  # mypy assertion
        try:
            # High-performance JSON serialization
            serialized = json.dumps(message, separators=(",", ":"), ensure_ascii=False)

            # Publish with timing measurement
            start_time = time.perf_counter()
            result = await self._redis.publish(channel, serialized)
            elapsed = (time.perf_counter() - start_time) * 1000

            # Log performance warning if >1ms
            if elapsed > 1.0:
                logger.warning(f"Publish latency {elapsed:.2f}ms exceeded 1ms target for channel '{channel}'")

            logger.debug(f"Published to '{channel}' in {elapsed:.3f}ms, {result} subscribers")
            return int(result)

        except (RedisError, json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to publish to channel '{channel}': {e}")
            raise PublishError(f"Failed to publish message: {e}") from e

    async def subscribe(self, channel: str, handler: MessageHandler) -> None:
        """Subscribe to Redis channel with message handler.

        Args:
        ----
            channel: Redis channel name to subscribe to
            handler: Async function to handle received messages

        Raises:
        ------
            SubscribeError: If subscription fails

        """
        if not self._connected or not self._redis:
            await self.connect()

        assert self._redis is not None  # mypy assertion
        try:
            # Initialize pubsub if needed
            if not self._pubsub:
                self._pubsub = self._redis.pubsub()

            # Add handler to channel handlers
            if channel not in self._handlers:
                self._handlers[channel] = []
            self._handlers[channel].append(handler)

            # Subscribe to channel if not already subscribed
            if channel not in self._subscribers:
                assert self._pubsub is not None  # mypy assertion
                await self._pubsub.subscribe(channel)
                self._subscribers.add(channel)
                logger.info(f"Subscribed to channel '{channel}'")

            # Start listening task if not already running
            if not self._listening_task or self._listening_task.done():
                self._listening_task = asyncio.create_task(self._listen_loop())

        except RedisError as e:
            logger.error(f"Failed to subscribe to channel '{channel}': {e}")
            raise SubscribeError(f"Failed to subscribe: {e}") from e

    async def unsubscribe(self, channel: str, handler: MessageHandler | None = None) -> None:
        """Unsubscribe from Redis channel.

        Args:
        ----
            channel: Redis channel name to unsubscribe from
            handler: Specific handler to remove (if None, removes all handlers)

        Raises:
        ------
            SubscribeError: If unsubscription fails

        """
        if not self._pubsub or channel not in self._subscribers:
            return

        try:
            # Remove specific handler or all handlers
            if handler and channel in self._handlers:
                if handler in self._handlers[channel]:
                    self._handlers[channel].remove(handler)

                # If no handlers left, unsubscribe from channel
                if not self._handlers[channel]:
                    del self._handlers[channel]
                    await self._pubsub.unsubscribe(channel)
                    self._subscribers.remove(channel)
                    logger.info(f"Unsubscribed from channel '{channel}'")
            else:
                # Remove all handlers and unsubscribe
                if channel in self._handlers:
                    del self._handlers[channel]
                await self._pubsub.unsubscribe(channel)
                self._subscribers.remove(channel)
                logger.info(f"Unsubscribed from channel '{channel}' (all handlers)")

        except RedisError as e:
            logger.error(f"Failed to unsubscribe from channel '{channel}': {e}")
            raise SubscribeError(f"Failed to unsubscribe: {e}") from e

    async def _listen_loop(self) -> None:
        """Process incoming messages in main listening loop."""
        if not self._pubsub:
            return

        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    await self._handle_message(message)

        except asyncio.CancelledError:
            logger.debug("Pub/Sub listening loop cancelled")
            raise
        except RedisError as e:
            logger.error(f"Error in Pub/Sub listening loop: {e}")
            # Attempt reconnection
            try:
                await self.connect()
                if self._pubsub and self._subscribers:
                    # Re-subscribe to all channels
                    for channel in list(self._subscribers):
                        await self._pubsub.subscribe(channel)
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect: {reconnect_error}")

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Handle incoming Redis message by calling registered handlers.

        Args:
        ----
            message: Raw Redis message dictionary

        """
        channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
        data_bytes = message["data"]

        if channel not in self._handlers:
            return

        try:
            # Deserialize JSON data
            data_str = data_bytes.decode("utf-8") if isinstance(data_bytes, bytes) else str(data_bytes)

            message_data = json.loads(data_str)

            # Call all handlers for this channel
            tasks: list[asyncio.Task[None]] = [
                asyncio.create_task(handler(channel, message_data))  # type: ignore[arg-type]
                for handler in self._handlers[channel]
            ]

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to decode message from channel '{channel}': {e}")
        except Exception as e:
            logger.error(f"Error handling message from channel '{channel}': {e}")

    @asynccontextmanager
    async def channel_subscription(
        self, channel: str
    ) -> AsyncGenerator[Callable[[MessageHandler], Awaitable[None]], None]:
        """Context manager for temporary channel subscription.

        Args:
        ----
            channel: Redis channel name

        Yields:
        ------
            Function to add handlers to the subscription

        Example:
        -------
            async with pubsub.channel_subscription("test_channel") as add_handler:
                await add_handler(my_message_handler)
                # ... do work ...
            # Automatically unsubscribed when exiting context

        """
        handlers_added: list[MessageHandler] = []

        async def add_handler(handler: MessageHandler) -> None:
            await self.subscribe(channel, handler)
            handlers_added.append(handler)

        try:
            yield add_handler
        finally:
            # Clean up all handlers added in this context
            for handler in handlers_added:
                await self.unsubscribe(channel, handler)

    async def get_subscribers_count(self, channel: str) -> int:
        """Get the number of subscribers for a channel.

        Args:
        ----
            channel: Redis channel name

        Returns:
        -------
            Number of active subscribers

        """
        if not self._connected or not self._redis:
            await self.connect()

        assert self._redis is not None  # mypy assertion
        try:
            result = await self._redis.pubsub_numsub(channel)
            return int(result[channel]) if channel in result else 0
        except RedisError as e:
            logger.error(f"Failed to get subscriber count for channel '{channel}': {e}")
            return 0

    @property
    def is_connected(self) -> bool:
        """Check if Redis connection is active."""
        return self._connected

    @property
    def active_subscriptions(self) -> set[str]:
        """Get set of currently subscribed channels."""
        return self._subscribers.copy()


# Global singleton instance
_pubsub_instance: RedisPubSub | None = None


async def get_pubsub() -> RedisPubSub:
    """Get singleton Redis Pub/Sub instance.

    Returns
    -------
        Configured RedisPubSub instance

    """
    global _pubsub_instance
    if _pubsub_instance is None:
        _pubsub_instance = RedisPubSub()
        await _pubsub_instance.connect()
    return _pubsub_instance


async def cleanup_pubsub() -> None:
    """Clean up singleton Pub/Sub instance."""
    global _pubsub_instance
    if _pubsub_instance:
        await _pubsub_instance.disconnect()
        _pubsub_instance = None
