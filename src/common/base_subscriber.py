"""Base subscriber for Redis Pub/Sub with async iterator support and reliability features.

This module provides the foundation for L2 consumers with:
- Asynchronous lifecycle methods (start_consuming, stop_consuming)
- Abstract process_message hook for domain logic
- Message acknowledgement pattern (even for Redis Pub/Sub)
- Error recovery with CircuitBreaker integration
- Batch processing option
- Dead-letter queue (DLQ) for permanently failed messages
- Pure asyncio implementation with bounded parallelism
- Observability via structured logging
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

# Import async_timeout with graceful degradation
try:
    import async_timeout

    _ASYNC_TIMEOUT_AVAILABLE = True
except ImportError:
    _ASYNC_TIMEOUT_AVAILABLE = False

    # Create a dummy module for type checking
    class DummyAsyncTimeout:
        """Dummy async_timeout class for type checking when module is not available."""

        @staticmethod
        def timeout(seconds: float) -> object:
            """Create a dummy timeout object.

            Args:
            ----
                seconds: Timeout duration (unused in dummy implementation)

            Returns:
            -------
                None placeholder object

            """
            return None

    async_timeout = DummyAsyncTimeout()

from .pubsub import CircuitBreaker, get_pubsub

logger = logging.getLogger(__name__)

# Type aliases
MessageDict = dict[str, Any]
DLQPublishFunc = Callable[[MessageDict], Awaitable[None]]

# Configuration constants
DEFAULT_ACK_TIMEOUT = 5.0
DEFAULT_MAX_CONCURRENCY = 32
DEFAULT_BATCH_SIZE = 100
DEFAULT_BATCH_WINDOW = 0.5  # seconds
DEFAULT_MESSAGE_TTL = 300  # 5 minutes for ACK tracking


class BaseSubscriber(ABC):
    """Foundation for L2 consumers with reliability and performance features.

    This abstract base class provides:
    - Async lifecycle management (start_consuming, stop_consuming)
    - Circuit breaker integration for fault tolerance
    - Message acknowledgement tracking via Redis
    - Dead letter queue support for failed messages
    - Batch processing capabilities
    - Bounded concurrency with semaphore
    - Timeout protection for slow handlers
    - Structured logging integration
    """

    def __init__(
        self,
        *,
        concurrency: int = DEFAULT_MAX_CONCURRENCY,
        circuit_breaker: CircuitBreaker | None = None,
        ack_timeout: float = DEFAULT_ACK_TIMEOUT,
        dlq_publish: DLQPublishFunc | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        batch_window: float = DEFAULT_BATCH_WINDOW,
        message_ttl: int = DEFAULT_MESSAGE_TTL,
    ) -> None:
        """Initialize BaseSubscriber with configuration parameters.

        Args:
        ----
            concurrency: Maximum number of concurrent message processors
            circuit_breaker: Optional circuit breaker for fault tolerance
            ack_timeout: Timeout in seconds for individual message processing
            dlq_publish: Optional function to publish failed messages to DLQ
            batch_size: Number of messages to collect before processing batch
            batch_window: Time window in seconds to wait for batch completion
            message_ttl: Time-to-live in seconds for message acknowledgement tracking

        """
        self._concurrency = concurrency
        self._sem = asyncio.Semaphore(concurrency)
        self._circuit_breaker = circuit_breaker
        self._ack_timeout = ack_timeout
        self._dlq_publish = dlq_publish
        self._batch_size = batch_size
        self._batch_window = batch_window
        self._message_ttl = message_ttl

        # Runtime state
        self._consuming_tasks: set[asyncio.Task[None]] = set()
        self._stop_event = asyncio.Event()
        self._channels: set[str] = set()

        # Batch processing state
        self._batch_buffer: list[MessageDict] = []
        self._batch_lock = asyncio.Lock()
        self._batch_task: asyncio.Task[None] | None = None

        # Metrics
        self._processed_count = 0
        self._failed_count = 0
        self._ack_success_count = 0
        self._ack_failed_count = 0
        self._dlq_count = 0

    # ----- Abstract hook --------------------------------------------------
    @abstractmethod
    async def process_message(self, message: MessageDict) -> bool:
        """Process a single message.

        Args:
        ----
            message: Message data as dictionary

        Returns:
        -------
            True if message was processed successfully, False to send to DLQ

        """
        ...

    async def process_batch(self, messages: list[MessageDict]) -> list[bool]:
        """Process a batch of messages.

        Default implementation calls process_message for each message.
        Override for custom batch processing logic.

        Args:
        ----
            messages: List of message dictionaries to process

        Returns:
        -------
            List of boolean results indicating success/failure for each message

        """
        results = []
        for message in messages:
            try:
                result = await self.process_message(message)
                results.append(result)
            except Exception:
                # Catch all exceptions during message processing to prevent batch failure
                results.append(False)
        return results

    # ----- Public API -----------------------------------------------------
    async def start_consuming(self, channel: str) -> None:
        """Start consuming messages from a Redis channel.

        Args:
        ----
            channel: Redis channel name to subscribe to

        """
        if channel in self._channels:
            logger.warning("Already consuming from channel '%s'", channel)
            return

        self._stop_event.clear()
        self._channels.add(channel)

        # Start consuming task
        task = asyncio.create_task(self._consume_loop(channel), name=f"{channel}-consumer")
        self._consuming_tasks.add(task)

        # Start batch processing task if not already running
        if not self._batch_task or self._batch_task.done():
            self._batch_task = asyncio.create_task(self._batch_processing_loop(), name="batch-processor")

        logger.info("Started consuming from channel '%s'", channel)

    async def stop_consuming(self) -> None:
        """Stop consuming messages and clean up resources."""
        self._stop_event.set()

        # Cancel all consuming tasks
        for task in self._consuming_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._consuming_tasks:
            await asyncio.gather(*self._consuming_tasks, return_exceptions=True)

        # Cancel batch processing task
        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._batch_task

        # Process any remaining messages in batch
        async with self._batch_lock:
            if self._batch_buffer:
                await self._process_batch_buffer()

        self._consuming_tasks.clear()
        self._channels.clear()
        self._batch_task = None

        logger.info("Stopped consuming from all channels")

    # ----- Internal logic -------------------------------------------------
    async def _consume_loop(self, channel: str) -> None:
        """Consume messages from a specific channel."""
        try:
            async for message in subscribe_to_channel(channel):
                if self._stop_event.is_set():
                    break

                # Add unique message ID for acknowledgement tracking
                message_id = str(uuid.uuid4())
                message["_subscriber_message_id"] = message_id

                # Acquire semaphore and process message
                await self._sem.acquire()

                if self._batch_size > 1:
                    # Add to batch
                    async with self._batch_lock:
                        self._batch_buffer.append(message)

                        # Process batch if it's full
                        if len(self._batch_buffer) >= self._batch_size:
                            await self._process_batch_buffer()

                    # Release semaphore since we're not processing immediately
                    self._sem.release()
                else:
                    # Process immediately
                    task = asyncio.create_task(self._handle_single_message(message))
                    # Don't await, let it run in background
                    task.add_done_callback(lambda _: None)

        except asyncio.CancelledError:
            logger.debug("Consumer loop for channel '%s' was cancelled", channel)
            raise
        except Exception:
            # Catch all exceptions to prevent consumer loop from crashing
            logger.exception("Error in consumer loop for channel '%s'", channel)
        finally:
            if channel in self._channels:
                self._channels.remove(channel)

    async def _batch_processing_loop(self) -> None:
        """Background task to process batches based on time window."""
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(self._batch_window)

                async with self._batch_lock:
                    if self._batch_buffer:
                        await self._process_batch_buffer()

        except asyncio.CancelledError:
            logger.debug("Batch processing loop was cancelled")
            raise
        except Exception:
            # Catch all exceptions to prevent batch processing loop from crashing
            logger.exception("Error in batch processing loop")

    async def _process_batch_buffer(self) -> None:
        """Process current batch buffer (must be called with _batch_lock held)."""
        if not self._batch_buffer:
            return

        batch = self._batch_buffer.copy()
        self._batch_buffer.clear()

        # Process batch in background
        task = asyncio.create_task(self._handle_message_batch(batch))
        # Don't await, let it run in background
        task.add_done_callback(lambda _: None)

    async def _handle_message_batch(self, messages: list[MessageDict]) -> None:
        """Handle a batch of messages."""
        try:
            # Acquire semaphores for all messages in batch
            semaphores = []
            for _ in messages:
                await self._sem.acquire()
                semaphores.append(True)

            # Set processing state for all messages
            processing_keys: list[str | None] = []
            for message in messages:
                message_id = message.get("_subscriber_message_id")
                if message_id:
                    processing_key = await self._set_processing_state(message_id)
                    processing_keys.append(processing_key)
                else:
                    processing_keys.append(None)

            # Process the batch
            if _ASYNC_TIMEOUT_AVAILABLE and async_timeout:
                async with async_timeout.timeout(self._ack_timeout):
                    results = await self._with_circuit_breaker(self.process_batch)(messages)
            else:
                results = await asyncio.wait_for(
                    self._with_circuit_breaker(self.process_batch)(messages),
                    timeout=self._ack_timeout,
                )

            # Handle results
            for message, result, processing_key in zip(messages, results, processing_keys, strict=False):  # type: ignore[assignment]
                await self._handle_message_result(message, success=result, processing_key=processing_key)
                self._processed_count += 1

        except Exception:
            logger.exception("Error processing message batch")
            # Handle all messages as failed
            for message, processing_key in zip(messages, processing_keys, strict=False):  # type: ignore[assignment]
                await self._handle_message_result(message, success=False, processing_key=processing_key)
                self._failed_count += 1
        finally:
            # Release all semaphores
            for _ in semaphores:
                self._sem.release()

    async def _handle_single_message(self, message: MessageDict) -> None:
        """Handle a single message with full error handling and ACK pattern."""
        message_id = message.get("_subscriber_message_id")
        processing_key = None

        try:
            # Set processing state
            if message_id:
                processing_key = await self._set_processing_state(message_id)

            # Process message with timeout
            if _ASYNC_TIMEOUT_AVAILABLE and async_timeout:
                async with async_timeout.timeout(self._ack_timeout):
                    result = await self._with_circuit_breaker(self.process_message)(message)
            else:
                result = await asyncio.wait_for(
                    self._with_circuit_breaker(self.process_message)(message),
                    timeout=self._ack_timeout,
                )

            await self._handle_message_result(message, success=result, processing_key=processing_key)
            self._processed_count += 1

        except Exception:
            logger.exception("Error processing message", extra={"msg_data": message})
            await self._handle_message_result(message, success=False, processing_key=processing_key)
            self._failed_count += 1
        finally:
            self._sem.release()

    async def _handle_message_result(
        self,
        message: MessageDict,
        *,
        success: bool,
        processing_key: str | None,
    ) -> None:
        """Handle the result of message processing."""
        if success:
            # Acknowledge successful processing
            if processing_key:
                await self._acknowledge_message(processing_key)
        else:
            # Send to DLQ if processing failed
            await self._send_to_dlq(message)
            if processing_key:
                await self._acknowledge_message(processing_key)  # Still ACK to prevent reprocessing

    async def _set_processing_state(self, message_id: str) -> str:
        """Set processing state in Redis for acknowledgement tracking."""
        processing_key = f"processing:{message_id}"
        try:
            pubsub = await get_pubsub()
            redis_client = pubsub._redis
            if redis_client:
                await redis_client.setex(processing_key, self._message_ttl, "1")
        except Exception:
            logger.exception("Failed to set processing state for %s", message_id)
        return processing_key

    async def _acknowledge_message(self, processing_key: str) -> None:
        """Acknowledge message processing by removing processing key."""
        try:
            pubsub = await get_pubsub()
            redis_client = pubsub._redis
            if redis_client:
                result = await redis_client.delete(processing_key)
                if result:
                    self._ack_success_count += 1
                else:
                    self._ack_failed_count += 1
        except Exception:
            logger.exception("Failed to acknowledge message %s", processing_key)
            self._ack_failed_count += 1

    async def _send_to_dlq(self, message: MessageDict) -> None:
        """Send failed message to dead letter queue."""
        if self._dlq_publish:
            try:
                # Add failure metadata
                dlq_message = {
                    **message,
                    "_dlq_timestamp": time.time(),
                    "_dlq_failure_reason": "processing_failed",
                }
                await self._dlq_publish(dlq_message)
                self._dlq_count += 1
            except Exception:
                logger.exception("Failed to send message to DLQ", extra={"msg_data": message})

    def _with_circuit_breaker(self, func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        """Wrap function with circuit breaker if available."""
        if not self._circuit_breaker:
            return func

        async def wrapper(*args: object, **kwargs: object) -> object:
            # We know _circuit_breaker is not None due to the check above
            return await self._circuit_breaker.call(func, *args, **kwargs)  # type: ignore[union-attr]

        return wrapper

    # ----- Metrics and observability --------------------------------------
    @property
    def metrics(self) -> dict[str, Any]:
        """Get subscriber metrics for monitoring."""
        return {
            "processed_count": self._processed_count,
            "failed_count": self._failed_count,
            "ack_success_count": self._ack_success_count,
            "ack_failed_count": self._ack_failed_count,
            "dlq_count": self._dlq_count,
            "active_channels": len(self._channels),
            "batch_buffer_size": len(self._batch_buffer),
            "concurrency_limit": self._concurrency,
            "circuit_breaker_metrics": self._circuit_breaker.metrics if self._circuit_breaker else None,
        }

    @property
    def is_consuming(self) -> bool:
        """Check if subscriber is actively consuming messages."""
        return bool(self._channels and not self._stop_event.is_set())

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on subscriber."""
        return {
            "status": "healthy" if self.is_consuming else "stopped",
            "active_channels": list(self._channels),
            "metrics": self.metrics,
        }


# ----- Async iterator support for channel subscription -----------------
async def subscribe_to_channel(channel: str, *, max_idle_time: float = 30.0) -> AsyncGenerator[MessageDict, None]:
    """Async iterator for subscribing to Redis channel messages.

    This function provides the async iterator interface that BaseSubscriber
    expects for consuming messages from Redis channels.

    SAFETY: Uses timeout-based approach to prevent infinite waiting that can
    hang tests. The generator will exit gracefully if no messages are received
    within max_idle_time seconds, allowing proper cleanup and test completion.

    Args:
    ----
        channel: Redis channel name to subscribe to
        max_idle_time: Maximum seconds to wait for messages before exiting (default: 30.0)

    Yields:
    ------
        Message dictionaries from the channel

    """
    pubsub = await get_pubsub()

    # Use the existing subscription mechanism with a custom handler
    message_queue: asyncio.Queue[MessageDict] = asyncio.Queue()

    async def message_handler(_ch: str, message: MessageDict) -> None:
        """Put messages in the queue."""
        await message_queue.put(message)

    # Subscribe to the channel
    await pubsub.subscribe(channel, message_handler)

    try:
        while True:
            try:
                # Wait for message with timeout to prevent infinite hanging
                if _ASYNC_TIMEOUT_AVAILABLE and async_timeout:
                    async with async_timeout.timeout(max_idle_time):
                        message = await message_queue.get()
                else:
                    message = await asyncio.wait_for(message_queue.get(), timeout=max_idle_time)

                yield message

            except TimeoutError:
                # Timeout reached with no messages - exit gracefully
                logger.debug("No messages received on channel '%s' for %ss, exiting iterator", channel, max_idle_time)
                break
            except Exception:
                # Other errors - log and exit gracefully
                logger.exception("Error in subscribe_to_channel for '%s'", channel)
                break

    finally:
        # Clean up subscription - this ensures proper cleanup even if generator
        # is cancelled or exits due to timeout
        try:
            await pubsub.unsubscribe(channel, message_handler)
            logger.debug("Unsubscribed from channel '%s'", channel)
        except Exception:
            logger.exception("Error during unsubscribe from '%s'", channel)


# ----- DLQ helper function ---------------------------------------------
async def publish_to_dlq(channel: str, message: MessageDict) -> None:
    """Publish a message to the dead letter queue.

    Messages are published to a DLQ channel with the pattern: dlq:{original_channel}

    Args:
    ----
        channel: Original channel name
        message: Failed message to send to DLQ

    """
    dlq_channel = f"dlq:{channel}"

    # Add DLQ metadata
    dlq_message = {
        **message,
        "_dlq_original_channel": channel,
        "_dlq_timestamp": time.time(),
        "_dlq_version": "1.0",
    }

    pubsub = await get_pubsub()
    await pubsub.publish(dlq_channel, dlq_message)

    logger.info("Published message to DLQ channel '%s'", dlq_channel)
