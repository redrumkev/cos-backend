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
from enum import Enum
from typing import TYPE_CHECKING, Any

# Import Redis with graceful degradation - use Any for type hints to avoid linter issues
if TYPE_CHECKING:
    # These imports are only for type checking and won't be resolved by linter
    pass

logger = logging.getLogger(__name__)

# Import redis with runtime checks
try:
    import redis.asyncio as redis
    from redis.asyncio import ConnectionPool
    from redis.exceptions import (
        ConnectionError as RedisConnectionError,
        RedisError,
        TimeoutError as RedisTimeoutError,
    )

    _REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis package not available. Pub/Sub functionality will be disabled.")
    redis = None
    ConnectionPool = None
    RedisConnectionError = Exception
    RedisError = Exception
    RedisTimeoutError = Exception
    _REDIS_AVAILABLE = False

from .redis_config import get_redis_config  # noqa: E402

# Type aliases for clarity
MessageHandler = Callable[[str, dict[str, Any]], Awaitable[None]]
MessageData = dict[str, Any]


class CircuitBreakerState(Enum):
    """Circuit breaker states following the standard pattern."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Failing fast, requests are rejected
    HALF_OPEN = "half_open"  # Testing recovery, limited requests allowed


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""


class CircuitBreaker:
    """Thread-safe circuit breaker implementation for Redis operations.

    Implements the circuit breaker pattern to prevent cascading failures
    during Redis unavailability. Supports three states:
    - CLOSED: Normal operation
    - OPEN: Failing fast to prevent cascading failures
    - HALF_OPEN: Testing recovery with limited requests

    Features:
    - Configurable failure thresholds and timeouts
    - Exponential backoff with jitter for recovery attempts
    - Thread-safe state management using asyncio.Lock
    - Metrics tracking for monitoring and observability
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 3,
        timeout: float = 10.0,
        expected_exception: type[Exception] | tuple[type[Exception], ...] = Exception,
    ) -> None:
        """Initialize circuit breaker with configuration parameters.

        Args:
        ----
            failure_threshold: Number of consecutive failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery (OPEN -> HALF_OPEN)
            success_threshold: Number of consecutive successes needed to close circuit in HALF_OPEN
            timeout: Timeout in seconds for individual operations
            expected_exception: Exception type(s) that should trigger circuit breaker

        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        # State management
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._next_attempt_time: float | None = None
        
        # Special case: if failure_threshold is 0, start in OPEN state (always fail fast)
        if failure_threshold == 0:
            self._state = CircuitBreakerState.OPEN
            self._next_attempt_time = float("inf")  # Never allow attempts
        else:
            self._state = CircuitBreakerState.CLOSED

        # Thread safety
        self._lock = asyncio.Lock()

        # Metrics for monitoring
        self._total_requests = 0
        self._total_failures = 0
        self._total_successes = 0
        self._state_transitions: dict[str, int] = {
            "closed_to_open": 0,
            "open_to_half_open": 0,
            "half_open_to_closed": 0,
            "half_open_to_open": 0,
        }

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    @property
    def success_count(self) -> int:
        """Get current success count in HALF_OPEN state."""
        return self._success_count

    @property
    def metrics(self) -> dict[str, Any]:
        """Get circuit breaker metrics for monitoring."""
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_requests": self._total_requests,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "failure_rate": self._total_failures / max(1, self._total_requests),
            "state_transitions": self._state_transitions.copy(),
            "last_failure_time": self._last_failure_time,
            "next_attempt_time": self._next_attempt_time,
        }

    async def _can_attempt_request(self) -> bool:
        """Check if a request can be attempted based on current state."""
        current_time = time.time()

        if self._state == CircuitBreakerState.CLOSED:
            return True
        elif self._state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has elapsed
            if self._next_attempt_time is not None and current_time >= self._next_attempt_time:
                await self._transition_to_half_open()
                return True
            return False
        elif self._state == CircuitBreakerState.HALF_OPEN:
            # Allow limited requests in half-open state
            return True

        return False

    async def _transition_to_open(self) -> None:
        """Transition circuit breaker to OPEN state."""
        if self._state != CircuitBreakerState.OPEN:
            previous_state = self._state.value
            self._state = CircuitBreakerState.OPEN
            self._last_failure_time = time.time()

            # Calculate next attempt time with exponential backoff
            backoff_multiplier = min(2 ** (self._failure_count - self.failure_threshold), 8)
            jitter = (time.time() % 1) * 0.1  # Add jitter to prevent thundering herd
            self._next_attempt_time = self._last_failure_time + (self.recovery_timeout * backoff_multiplier) + jitter

            # Track state transition
            if previous_state == "closed":
                self._state_transitions["closed_to_open"] += 1
            elif previous_state == "half_open":
                self._state_transitions["half_open_to_open"] += 1

            logger.warning(
                f"Circuit breaker opened after {self._failure_count} failures. "
                f"Next attempt at {self._next_attempt_time}"
            )

    async def _transition_to_half_open(self) -> None:
        """Transition circuit breaker to HALF_OPEN state."""
        if self._state != CircuitBreakerState.HALF_OPEN:
            self._state = CircuitBreakerState.HALF_OPEN
            self._success_count = 0
            self._state_transitions["open_to_half_open"] += 1
            logger.info("Circuit breaker transitioned to HALF_OPEN - testing recovery")

    async def _transition_to_closed(self) -> None:
        """Transition circuit breaker to CLOSED state."""
        if self._state != CircuitBreakerState.CLOSED:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._next_attempt_time = None
            self._state_transitions["half_open_to_closed"] += 1
            logger.info("Circuit breaker closed - normal operation restored")

    async def _record_success(self) -> None:
        """Record a successful operation and update state if needed."""
        self._total_requests += 1
        self._total_successes += 1

        if self._state == CircuitBreakerState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                await self._transition_to_closed()
        elif self._state == CircuitBreakerState.CLOSED:
            # Reset failure count on success in closed state
            self._failure_count = 0

    async def _record_failure(self) -> None:
        """Record a failed operation and update state if needed."""
        self._total_requests += 1
        self._total_failures += 1
        self._failure_count += 1

        if self._state == CircuitBreakerState.CLOSED:
            # Special case: if failure_threshold is 0, open immediately on any failure
            if self.failure_threshold == 0 or self._failure_count >= self.failure_threshold:
                await self._transition_to_open()
        elif self._state == CircuitBreakerState.HALF_OPEN:
            # Any failure in half-open state transitions back to open
            await self._transition_to_open()

    async def call(self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
        """Execute a function with circuit breaker protection.

        Args:
        ----
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
        -------
            Result of the function call

        Raises:
        ------
            CircuitBreakerError: If circuit breaker is open
            Exception: Any exception raised by the wrapped function

        """
        async with self._lock:
            # Check if request can be attempted
            if not await self._can_attempt_request():
                raise CircuitBreakerError(
                    f"Circuit breaker is {self._state.value}. " f"Next attempt at {self._next_attempt_time}"
                )

        try:
            # Execute the function with timeout
            result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.timeout)

            # Record success
            async with self._lock:
                await self._record_success()

            return result

        except self.expected_exception:
            # Record failure for expected exceptions
            async with self._lock:
                await self._record_failure()
            raise
        except TimeoutError:
            # Treat timeouts as failures
            async with self._lock:
                await self._record_failure()
            raise
        except Exception:
            # For unexpected exceptions, don't count as circuit breaker failure
            # but still track in metrics
            async with self._lock:
                self._total_requests += 1
            raise


class PubSubError(Exception):
    """Base exception for Pub/Sub operations."""


class PublishError(PubSubError):
    """Exception raised when message publishing fails."""


class SubscribeError(PubSubError):
    """Exception raised when subscription operations fail."""


class RedisPubSub:
    """High-performance Redis Pub/Sub wrapper with connection pooling and circuit breaker.

    Designed for <1ms publish latency with automatic connection management,
    error handling, circuit breaker resilience, and JSON serialization/deserialization.
    """

    def __init__(self) -> None:
        """Initialize Redis Pub/Sub client with optimized connection pool and circuit breaker."""
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

        # Initialize circuit breaker for Redis operations
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=3,  # Open after 3 consecutive failures
            recovery_timeout=30.0,  # Wait 30s before attempting recovery
            success_threshold=2,  # Close after 2 consecutive successes
            timeout=5.0,  # 5s timeout for individual Redis operations
            expected_exception=(RedisError, RedisConnectionError, RedisTimeoutError),
        )

    async def connect(self) -> None:
        """Establish Redis connection with optimized pool settings and circuit breaker protection."""
        if self._connected:
            return

        if not _REDIS_AVAILABLE:
            raise PubSubError("Redis package is required for connection")

        async def _connect_operation() -> None:
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

            assert redis is not None, "Redis client not available"
            self._redis = redis.Redis(
                connection_pool=self._pool,
                decode_responses=False,  # Handle bytes for performance
            )

            # Test connection
            assert self._redis is not None  # mypy assertion
            await self._redis.ping()

        try:
            # Use circuit breaker to protect connection operation
            await self._circuit_breaker.call(_connect_operation)
            self._connected = True
            logger.info("Redis Pub/Sub connected successfully")

        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker prevented Redis connection: {e}")
            raise PubSubError(f"Redis connection blocked by circuit breaker: {e}") from e
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
        """Publish message to Redis channel with <1ms latency target and circuit breaker protection.

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
            CircuitBreakerError: If circuit breaker is open

        """
        if not self._connected or not self._redis:
            await self.connect()

        assert self._redis is not None  # mypy assertion

        # Pre-serialize JSON for performance
        try:
            serialized = json.dumps(message, separators=(",", ":"), ensure_ascii=False)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to serialize message for channel '{channel}': {e}")
            raise PublishError(f"Failed to serialize message: {e}") from e

        async def _publish_operation() -> int:
            # Publish with timing measurement
            start_time = time.perf_counter()
            result = await self._redis.publish(channel, serialized)
            elapsed = (time.perf_counter() - start_time) * 1000

            # Log performance warning if >1ms
            if elapsed > 1.0:
                logger.warning(f"Publish latency {elapsed:.2f}ms exceeded 1ms target for channel '{channel}'")

            logger.debug(f"Published to '{channel}' in {elapsed:.3f}ms, {result} subscribers")
            return int(result)

        try:
            # Use circuit breaker to protect publish operation
            result = await self._circuit_breaker.call(_publish_operation)
            return int(result)

        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker prevented publish to channel '{channel}': {e}")
            raise PublishError(f"Publish blocked by circuit breaker: {e}") from e
        except RedisError as e:
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
        """Get the number of subscribers for a channel with circuit breaker protection.

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

        async def _get_count_operation() -> int:
            result = await self._redis.pubsub_numsub(channel)
            return int(result[channel]) if channel in result else 0

        try:
            result = await self._circuit_breaker.call(_get_count_operation)
            return int(result)
        except (CircuitBreakerError, RedisError) as e:
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

    @property
    def circuit_breaker_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._circuit_breaker.state

    @property
    def circuit_breaker_metrics(self) -> dict[str, Any]:
        """Get circuit breaker metrics for monitoring."""
        return self._circuit_breaker.metrics

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on Redis connection and circuit breaker.

        Returns
        -------
            Health status dictionary with connection and circuit breaker info

        """
        health_status = {
            "connected": self._connected,
            "circuit_breaker": {
                "state": self._circuit_breaker.state.value,
                "metrics": self._circuit_breaker.metrics,
            },
            "redis_available": _REDIS_AVAILABLE,
            "active_subscriptions": len(self._subscribers),
        }

        # Test Redis connection if available
        if self._connected and self._redis:
            try:

                async def _ping_operation() -> bool:
                    await self._redis.ping()
                    return True

                await self._circuit_breaker.call(_ping_operation)
                health_status["redis_ping"] = "success"
            except (CircuitBreakerError, RedisError) as e:
                health_status["redis_ping"] = f"failed: {e}"
        else:
            health_status["redis_ping"] = "not_connected"

        return health_status


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
