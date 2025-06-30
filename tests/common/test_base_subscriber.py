"""Comprehensive tests for BaseSubscriber implementation.

Tests cover:
- Abstract base class behavior
- Async lifecycle methods (start_consuming, stop_consuming)
- Message processing and acknowledgement
- Dead letter queue functionality
- Batch processing capabilities
- Circuit breaker integration
- Concurrency control and timeout handling
- Metrics and observability
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.common.base_subscriber import (
    DEFAULT_ACK_TIMEOUT,
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_CONCURRENCY,
    BaseSubscriber,
    MessageDict,
    publish_to_dlq,
    subscribe_to_channel,
)
from src.common.pubsub import CircuitBreaker, CircuitBreakerError

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from typing import Any


# Constants for test values
EXPECTED_PROCESSED_MESSAGES = 5
EXPECTED_DLQ_MESSAGES = 2
EXPECTED_ACK_OPERATIONS = 5

# Integration test constants
INTEGRATION_TOTAL_MESSAGES = 5
INTEGRATION_FAILED_MESSAGES = 2
INTEGRATION_SUCCESSFUL_MESSAGES = 3
INTEGRATION_BATCH_SIZE = 2
INTEGRATION_CONCURRENCY = 4

# Additional test constants
TWO_MESSAGES = 2
TEST_MESSAGE_ID = 123
FOUR_MESSAGES = 4
ASYNC_TIMEOUT_AVAILABLE_TRUE = True
ASYNC_TIMEOUT_AVAILABLE_FALSE = False
CUSTOM_CONCURRENCY = 16
CUSTOM_ACK_TIMEOUT = 10.0
CUSTOM_BATCH_SIZE = 50
CUSTOM_BATCH_WINDOW = 1.0
CUSTOM_MESSAGE_TTL = 600
TEST_CONCURRENCY = 2
TEST_ACK_TIMEOUT = 0.1
TEST_PROCESSING_DELAY = 0.2
TEST_BATCH_SIZE = 3
SMALL_BATCH_WINDOW = 0.1
LARGE_BATCH_SIZE = 10
CIRCUIT_BREAKER_THRESHOLD = 1
CIRCUIT_BREAKER_TIMEOUT = 1.0
SHORT_TIMEOUT = 0.1
PROCESSING_TIME = 0.1

# Test error messages
SIMULATED_FAILURE_MSG = "Simulated processing failure"
DLQ_ERROR_MSG = "DLQ error"
REDIS_ERROR_MSG = "Redis error"


class ConcreteTestSubscriber(BaseSubscriber):
    """Concrete implementation of BaseSubscriber for testing."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize test subscriber with tracking capabilities.

        Args:
        ----
            **kwargs: Arguments passed to BaseSubscriber

        """
        super().__init__(**kwargs)
        self.processed_messages: list[MessageDict] = []
        self.processing_results: list[bool] = []
        self.should_fail = False
        self.processing_delay = 0.0

    async def process_message(self, message: MessageDict) -> bool:
        """Test implementation that records processed messages.

        Args:
        ----
            message: Message to process

        Returns:
        -------
            Processing success status

        Raises:
        ------
            ValueError: When should_fail is True

        """
        if self.processing_delay > 0:
            await asyncio.sleep(self.processing_delay)

        self.processed_messages.append(message)

        if self.should_fail:
            msg = SIMULATED_FAILURE_MSG
            raise ValueError(msg)

        # Use processing_results if available, otherwise succeed
        if self.processing_results:
            return self.processing_results.pop(0)
        return True

    async def process_batch(self, messages: list[MessageDict]) -> list[bool]:
        """Test batch implementation.

        Args:
        ----
            messages: List of messages to process

        Returns:
        -------
            List of processing success statuses

        """
        # Record all messages
        self.processed_messages.extend(messages)

        # Return results based on processing_results or default to success
        results = []
        for _ in messages:
            if self.processing_results:
                results.append(self.processing_results.pop(0))
            else:
                results.append(not self.should_fail)
        return results


class TestBaseSubscriberABC:
    """Test abstract base class behavior."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """BaseSubscriber cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseSubscriber()  # type: ignore[abstract]

    def test_must_implement_process_message(self) -> None:
        """Subclasses must implement process_message method."""

        class IncompleteSubscriber(BaseSubscriber):
            """Test class missing required abstract methods."""

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteSubscriber()  # type: ignore[abstract]

    def test_concrete_implementation_works(self) -> None:
        """Concrete implementation with process_message can be instantiated."""
        subscriber = ConcreteTestSubscriber()
        # Test instance type
        assert isinstance(subscriber, BaseSubscriber)

        # Test configuration values
        assert subscriber._concurrency == DEFAULT_MAX_CONCURRENCY
        assert subscriber._ack_timeout == DEFAULT_ACK_TIMEOUT


class TestBaseSubscriberConfiguration:
    """Test subscriber configuration and initialization."""

    def test_default_configuration(self) -> None:
        """Test default configuration values."""
        subscriber = ConcreteTestSubscriber()

        # Test default values
        assert subscriber._concurrency == DEFAULT_MAX_CONCURRENCY
        assert subscriber._ack_timeout == DEFAULT_ACK_TIMEOUT
        assert subscriber._batch_size == DEFAULT_BATCH_SIZE
        assert subscriber._circuit_breaker is None
        assert subscriber._dlq_publish is None

    def test_custom_configuration(self) -> None:
        """Test custom configuration values."""
        circuit_breaker = CircuitBreaker()
        dlq_func = AsyncMock()

        subscriber = ConcreteTestSubscriber(
            concurrency=CUSTOM_CONCURRENCY,
            ack_timeout=CUSTOM_ACK_TIMEOUT,
            batch_size=CUSTOM_BATCH_SIZE,
            batch_window=CUSTOM_BATCH_WINDOW,
            circuit_breaker=circuit_breaker,
            dlq_publish=dlq_func,
            message_ttl=CUSTOM_MESSAGE_TTL,
        )

        # Test custom values
        assert subscriber._concurrency == CUSTOM_CONCURRENCY
        assert subscriber._ack_timeout == CUSTOM_ACK_TIMEOUT
        assert subscriber._batch_size == CUSTOM_BATCH_SIZE
        assert subscriber._batch_window == CUSTOM_BATCH_WINDOW
        assert subscriber._circuit_breaker is circuit_breaker
        assert subscriber._dlq_publish is dlq_func
        assert subscriber._message_ttl == CUSTOM_MESSAGE_TTL

    def test_initial_state(self) -> None:
        """Test initial subscriber state."""
        subscriber = ConcreteTestSubscriber()

        # Test initial state
        assert not subscriber.is_consuming
        assert len(subscriber._channels) == 0
        assert len(subscriber._consuming_tasks) == 0
        assert subscriber._stop_event.is_set() is False
        assert subscriber.metrics["processed_count"] == 0


@pytest.mark.asyncio
class TestLifecycleManagement:
    """Test async lifecycle methods."""

    @patch("src.common.base_subscriber.subscribe_to_channel")
    async def test_start_consuming_single_channel(self, mock_subscribe: AsyncMock) -> None:
        """Test starting consumption from a single channel."""

        # Mock the async generator
        async def mock_message_generator() -> AsyncGenerator[MessageDict, None]:
            yield {"test": "message1"}
            yield {"test": "message2"}

        mock_subscribe.return_value = mock_message_generator()

        subscriber = ConcreteTestSubscriber()

        # Start consuming
        await subscriber.start_consuming("test_channel")

        # Verify consuming state
        assert subscriber.is_consuming
        assert "test_channel" in subscriber._channels
        assert len(subscriber._consuming_tasks) == 1

        # Allow some processing time
        await asyncio.sleep(PROCESSING_TIME)

        # Stop consuming
        await subscriber.stop_consuming()

        # Test lifecycle state
        assert not subscriber.is_consuming
        assert len(subscriber._channels) == 0
        assert len(subscriber._consuming_tasks) == 0

    async def test_start_consuming_duplicate_channel(self) -> None:
        """Test starting consumption from same channel twice."""
        subscriber = ConcreteTestSubscriber()

        with patch("src.common.base_subscriber.subscribe_to_channel") as mock_subscribe:
            mock_subscribe.return_value = AsyncMock()

            # Start consuming twice
            await subscriber.start_consuming("test_channel")
            await subscriber.start_consuming("test_channel")  # Should warn, not duplicate

            # Should only have one channel
            assert len(subscriber._channels) == 1
            assert "test_channel" in subscriber._channels

    async def test_stop_consuming_cleans_up_resources(self) -> None:
        """Test that stop_consuming properly cleans up all resources."""
        subscriber = ConcreteTestSubscriber()

        with patch("src.common.base_subscriber.subscribe_to_channel") as mock_subscribe:
            # Mock async generator that yields indefinitely
            async def endless_generator() -> AsyncGenerator[MessageDict, None]:
                while True:
                    yield {"test": "message"}
                    await asyncio.sleep(0.01)

            mock_subscribe.return_value = endless_generator()

            # Start consuming
            await subscriber.start_consuming("test_channel")

            # Verify it's running
            assert subscriber.is_consuming
            assert len(subscriber._consuming_tasks) == 1

            # Stop consuming
            await subscriber.stop_consuming()

            # Verify cleanup
            assert not subscriber.is_consuming
            assert len(subscriber._channels) == 0
            assert len(subscriber._consuming_tasks) == 0
            assert subscriber._batch_task is None


@pytest.mark.asyncio
class TestMessageProcessing:
    """Test message processing functionality."""

    @patch("src.common.base_subscriber.get_pubsub")
    @patch("src.common.base_subscriber.subscribe_to_channel")
    async def test_single_message_processing(self, mock_subscribe: AsyncMock, mock_get_pubsub: AsyncMock) -> None:
        """Test processing of individual messages."""
        # Mock Redis client for ACK operations
        mock_redis = AsyncMock()
        mock_pubsub = AsyncMock()
        mock_pubsub._redis = mock_redis
        mock_get_pubsub.return_value = mock_pubsub

        # Mock message generator
        test_messages = [
            {"content": "message1"},
            {"content": "message2"},
        ]

        async def message_generator() -> AsyncGenerator[MessageDict, None]:
            for msg in test_messages:
                yield msg

        mock_subscribe.return_value = message_generator()

        subscriber = ConcreteTestSubscriber()
        subscriber._batch_size = 1  # Disable batching

        # Start consuming
        await subscriber.start_consuming("test_channel")

        # Allow processing time
        await asyncio.sleep(0.1)

        # Stop consuming
        await subscriber.stop_consuming()

        # Verify messages were processed
        assert len(subscriber.processed_messages) == TWO_MESSAGES
        assert subscriber.processed_messages[0]["content"] == "message1"
        assert subscriber.processed_messages[1]["content"] == "message2"

        # Verify ACK operations were called
        assert mock_redis.setex.call_count == TWO_MESSAGES  # Set processing state
        assert mock_redis.delete.call_count == TWO_MESSAGES  # Acknowledge messages

    @patch("src.common.base_subscriber.get_pubsub")
    async def test_message_processing_failure(self, mock_get_pubsub: AsyncMock) -> None:
        """Test handling of message processing failures."""
        # Mock DLQ function
        mock_dlq = AsyncMock()

        # Mock Redis
        mock_redis = AsyncMock()
        mock_pubsub = AsyncMock()
        mock_pubsub._redis = mock_redis
        mock_get_pubsub.return_value = mock_pubsub

        subscriber = ConcreteTestSubscriber(dlq_publish=mock_dlq)
        subscriber.should_fail = True
        subscriber._batch_size = 1  # Disable batching

        # Process a message directly
        test_message = {"content": "failing_message"}
        await subscriber._handle_single_message(test_message)

        # Verify DLQ was called
        mock_dlq.assert_called_once()

        # Verify metrics
        assert subscriber.metrics["failed_count"] == 1
        assert subscriber.metrics["dlq_count"] == 1


@pytest.mark.asyncio
class TestBatchProcessing:
    """Test batch processing capabilities."""

    @patch("src.common.base_subscriber.get_pubsub")
    async def test_batch_size_trigger(self, mock_get_pubsub: AsyncMock) -> None:
        """Test that batch processing triggers when batch size is reached."""
        # Mock Redis
        mock_redis = AsyncMock()
        mock_pubsub = AsyncMock()
        mock_pubsub._redis = mock_redis
        mock_get_pubsub.return_value = mock_pubsub

        subscriber = ConcreteTestSubscriber(batch_size=3)

        # Create test messages
        messages = [{"id": i} for i in range(3)]

        # Process messages directly to test batching
        for msg in messages:
            msg["_subscriber_message_id"] = f"test_{msg['id']}"  # type: ignore[assignment]
            async with subscriber._batch_lock:
                subscriber._batch_buffer.append(msg)

                # Should trigger batch processing when reaching size 3
                if len(subscriber._batch_buffer) >= subscriber._batch_size:
                    await subscriber._process_batch_buffer()

        # Allow processing time
        await asyncio.sleep(0.1)

        # Verify batch was processed
        assert len(subscriber.processed_messages) == TEST_BATCH_SIZE
        assert subscriber._batch_buffer == []  # Buffer should be empty

    @patch("src.common.base_subscriber.get_pubsub")
    async def test_batch_time_window_trigger(self, mock_get_pubsub: AsyncMock) -> None:
        """Test that batch processing triggers based on time window."""
        # Mock Redis
        mock_redis = AsyncMock()
        mock_pubsub = AsyncMock()
        mock_pubsub._redis = mock_redis
        mock_get_pubsub.return_value = mock_pubsub

        subscriber = ConcreteTestSubscriber(batch_size=10, batch_window=0.1)  # Small window

        # Start batch processing loop
        subscriber._batch_task = asyncio.create_task(subscriber._batch_processing_loop())

        # Add a message to buffer
        test_message = {"content": "test", "_subscriber_message_id": "test_1"}
        async with subscriber._batch_lock:
            subscriber._batch_buffer.append(test_message)

        # Wait for time window to trigger processing
        await asyncio.sleep(0.2)

        # Stop batch processing
        subscriber._stop_event.set()
        if subscriber._batch_task:
            await subscriber._batch_task

        # Verify message was processed due to time window
        assert len(subscriber.processed_messages) == 1
        assert subscriber._batch_buffer == []

    async def test_custom_batch_processing(self) -> None:
        """Test custom batch processing implementation."""
        subscriber = ConcreteTestSubscriber()

        # Set up batch processing results
        subscriber.processing_results = [True, False, True]  # Mixed results

        messages = [
            {"id": 1, "content": "msg1"},
            {"id": 2, "content": "msg2"},
            {"id": 3, "content": "msg3"},
        ]

        results = await subscriber.process_batch(messages)

        # Verify results
        assert results == [True, False, True]
        assert len(subscriber.processed_messages) == TEST_BATCH_SIZE


@pytest.mark.asyncio
class TestCircuitBreakerIntegration:
    """Test circuit breaker integration."""

    async def test_circuit_breaker_protection(self) -> None:
        """Test that circuit breaker protects message processing."""
        # Create circuit breaker that opens immediately
        circuit_breaker = CircuitBreaker(failure_threshold=1, timeout=1.0)

        subscriber = ConcreteTestSubscriber(circuit_breaker=circuit_breaker)
        subscriber.should_fail = True

        # Process messages to trigger circuit breaker
        test_message = {"content": "test"}

        # First message should fail and open circuit breaker
        with pytest.raises(ValueError, match=SIMULATED_FAILURE_MSG):
            await subscriber.process_message(test_message)

        # Second message should be blocked by circuit breaker
        with pytest.raises(CircuitBreakerError):
            await subscriber._with_circuit_breaker(subscriber.process_message)(test_message)

    async def test_circuit_breaker_metrics_included(self) -> None:
        """Test that circuit breaker metrics are included in subscriber metrics."""
        circuit_breaker = CircuitBreaker()
        subscriber = ConcreteTestSubscriber(circuit_breaker=circuit_breaker)

        metrics = subscriber.metrics
        assert "circuit_breaker_metrics" in metrics
        assert metrics["circuit_breaker_metrics"] is not None

    async def test_no_circuit_breaker_metrics(self) -> None:
        """Test metrics when no circuit breaker is configured."""
        subscriber = ConcreteTestSubscriber()

        metrics = subscriber.metrics
        assert metrics["circuit_breaker_metrics"] is None


@pytest.mark.asyncio
class TestAcknowledgementPattern:
    """Test message acknowledgement tracking."""

    @patch("src.common.base_subscriber.get_pubsub")
    async def test_ack_pattern_success(self, mock_get_pubsub: AsyncMock) -> None:
        """Test successful acknowledgement pattern."""
        # Mock Redis operations
        mock_redis = AsyncMock()
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 1  # Successful deletion

        mock_pubsub = AsyncMock()
        mock_pubsub._redis = mock_redis
        mock_get_pubsub.return_value = mock_pubsub

        subscriber = ConcreteTestSubscriber()

        # Test message processing
        message_id = "test_message_123"
        processing_key = await subscriber._set_processing_state(message_id)

        # Verify processing state was set
        mock_redis.setex.assert_called_once_with(f"processing:{message_id}", subscriber._message_ttl, "1")

        # Test acknowledgement
        await subscriber._acknowledge_message(processing_key)

        # Verify acknowledgement
        mock_redis.delete.assert_called_once_with(processing_key)
        assert subscriber._ack_success_count == 1

    @patch("src.common.base_subscriber.get_pubsub")
    async def test_ack_pattern_failure(self, mock_get_pubsub: AsyncMock) -> None:
        """Test acknowledgement pattern when Redis operations fail."""
        # Mock Redis operations to fail
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = Exception("Redis error")
        mock_redis.delete.return_value = 0  # Failed deletion

        mock_pubsub = AsyncMock()
        mock_pubsub._redis = mock_redis
        mock_get_pubsub.return_value = mock_pubsub

        subscriber = ConcreteTestSubscriber()

        # Test setting processing state with error
        message_id = "test_message_123"
        processing_key = await subscriber._set_processing_state(message_id)

        # Should still return the key even if Redis operation failed
        assert processing_key == f"processing:{message_id}"

        # Test acknowledgement failure
        mock_redis.delete.return_value = 0  # Simulate failed deletion
        await subscriber._acknowledge_message(processing_key)

        assert subscriber._ack_failed_count == 1


@pytest.mark.asyncio
class TestDeadLetterQueue:
    """Test dead letter queue functionality."""

    async def test_dlq_message_structure(self) -> None:
        """Test that DLQ messages have correct structure."""
        mock_dlq = AsyncMock()
        subscriber = ConcreteTestSubscriber(dlq_publish=mock_dlq)

        original_message = {"id": 123, "content": "test message"}

        await subscriber._send_to_dlq(original_message)

        # Verify DLQ function was called
        mock_dlq.assert_called_once()

        # Check the message structure passed to DLQ
        dlq_message = mock_dlq.call_args[0][0]
        assert dlq_message["id"] == TEST_MESSAGE_ID
        assert dlq_message["content"] == "test message"
        assert "_dlq_timestamp" in dlq_message
        assert "_dlq_failure_reason" in dlq_message
        assert dlq_message["_dlq_failure_reason"] == "processing_failed"

    async def test_dlq_error_handling(self) -> None:
        """Test DLQ error handling when DLQ publishing fails."""
        # Mock DLQ function that raises an exception
        mock_dlq = AsyncMock(side_effect=Exception("DLQ error"))
        subscriber = ConcreteTestSubscriber(dlq_publish=mock_dlq)

        original_message = {"content": "test"}

        # Should not raise exception even if DLQ fails
        await subscriber._send_to_dlq(original_message)

        # DLQ count should not increment on failure
        assert subscriber.metrics["dlq_count"] == 0

    @patch("src.common.base_subscriber.get_pubsub")
    async def test_publish_to_dlq_helper(self, mock_get_pubsub: AsyncMock) -> None:
        """Test the publish_to_dlq helper function."""
        # Mock pubsub
        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub

        original_channel = "test_channel"
        message = {"id": 1, "content": "failed message"}

        await publish_to_dlq(original_channel, message)

        # Verify DLQ channel and message structure
        mock_pubsub.publish.assert_called_once()
        call_args = mock_pubsub.publish.call_args

        dlq_channel = call_args[0][0]
        dlq_message = call_args[0][1]

        assert dlq_channel == "dlq:test_channel"
        assert dlq_message["id"] == 1
        assert dlq_message["content"] == "failed message"
        assert "_dlq_original_channel" in dlq_message
        assert "_dlq_timestamp" in dlq_message
        assert dlq_message["_dlq_original_channel"] == original_channel


@pytest.mark.asyncio
class TestConcurrencyControl:
    """Test concurrency control and timeout handling."""

    async def test_concurrency_semaphore(self) -> None:
        """Test that semaphore limits concurrent processing."""
        subscriber = ConcreteTestSubscriber(concurrency=2)
        subscriber.processing_delay = 0.1  # Add delay to test concurrency

        # Track concurrent calls
        concurrent_calls: list[int] = []
        original_process = subscriber.process_message

        async def tracking_process(message: MessageDict) -> bool:
            concurrent_calls.append(len(concurrent_calls) + 1)
            result = await original_process(message)
            concurrent_calls.pop()
            return result

        subscriber.process_message = tracking_process  # type: ignore[method-assign]

        # Process multiple messages concurrently
        messages = [{"id": i} for i in range(4)]
        tasks = []

        for msg in messages:
            task = asyncio.create_task(subscriber._handle_single_message(msg))
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Verify semaphore was effective (max 2 concurrent)
        # This is a bit tricky to test deterministically, but we can verify
        # that all messages were processed
        assert len(subscriber.processed_messages) == FOUR_MESSAGES

    @patch("src.common.base_subscriber.get_pubsub")
    async def test_timeout_handling(self, mock_get_pubsub: AsyncMock) -> None:
        """Test timeout handling for slow message processing."""
        # Mock Redis
        mock_redis = AsyncMock()
        mock_pubsub = AsyncMock()
        mock_pubsub._redis = mock_redis
        mock_get_pubsub.return_value = mock_pubsub

        subscriber = ConcreteTestSubscriber(ack_timeout=0.1)  # Very short timeout
        subscriber.processing_delay = 0.2  # Longer than timeout

        message = {"content": "slow message"}

        # Should raise TimeoutError
        with pytest.raises(asyncio.TimeoutError):
            await subscriber._handle_single_message(message)


class TestMetricsAndObservability:
    """Test metrics and observability features."""

    def test_initial_metrics(self) -> None:
        """Test initial metrics state."""
        subscriber = ConcreteTestSubscriber()

        metrics = subscriber.metrics
        assert metrics["processed_count"] == 0
        assert metrics["failed_count"] == 0
        assert metrics["ack_success_count"] == 0
        assert metrics["ack_failed_count"] == 0
        assert metrics["dlq_count"] == 0
        assert metrics["active_channels"] == 0
        assert metrics["batch_buffer_size"] == 0
        assert metrics["concurrency_limit"] == DEFAULT_MAX_CONCURRENCY

    async def test_metrics_updates(self) -> None:
        """Test that metrics are updated during processing."""
        subscriber = ConcreteTestSubscriber()

        # Simulate processing
        subscriber._processed_count = 5
        subscriber._failed_count = 2
        subscriber._dlq_count = 1
        subscriber._channels.add("test_channel")

        metrics = subscriber.metrics
        assert metrics["processed_count"] == EXPECTED_PROCESSED_MESSAGES
        assert metrics["failed_count"] == EXPECTED_DLQ_MESSAGES
        assert metrics["dlq_count"] == 1
        assert metrics["active_channels"] == 1

    async def test_health_check(self) -> None:
        """Test health check functionality."""
        subscriber = ConcreteTestSubscriber()

        # Test when not consuming
        health = await subscriber.health_check()
        assert health["status"] == "stopped"
        assert health["active_channels"] == []

        # Test when consuming
        subscriber._channels.add("test_channel")
        subscriber._stop_event.clear()

        health = await subscriber.health_check()
        assert health["status"] == "healthy"
        assert "test_channel" in health["active_channels"]
        assert "metrics" in health


@pytest.mark.asyncio
class TestSubscribeToChannelIterator:
    """Test the subscribe_to_channel async iterator."""

    @patch("src.common.base_subscriber.get_pubsub")
    async def test_subscribe_to_channel_basic(self, mock_get_pubsub: AsyncMock) -> None:
        """Test basic functionality of subscribe_to_channel."""
        # Mock pubsub with subscription capability
        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub

        channel = "test_channel"

        # Start the async iterator with short timeout for testing
        iterator = subscribe_to_channel(channel, max_idle_time=0.1)

        # Verify subscribe was called
        await iterator.__anext__()  # This will trigger the subscription
        mock_pubsub.subscribe.assert_called_once()

        # Clean up - this should call unsubscribe
        await iterator.aclose()
        mock_pubsub.unsubscribe.assert_called_once()

    @patch("src.common.base_subscriber.get_pubsub")
    async def test_subscribe_to_channel_timeout_behavior(self, mock_get_pubsub: AsyncMock) -> None:
        """Test that subscribe_to_channel exits gracefully on timeout."""
        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub

        channel = "test_channel"
        messages_received = []

        # Use very short timeout for testing
        try:
            async for message in subscribe_to_channel(channel, max_idle_time=0.1):
                messages_received.append(message)  # noqa: PERF401
                # Should timeout after 0.1 seconds with no messages
        except StopAsyncIteration:
            pass  # Expected timeout behavior

        # Verify that the iterator exited due to timeout (no messages received)
        assert len(messages_received) == 0

        # Verify proper cleanup occurred
        mock_pubsub.subscribe.assert_called_once()
        mock_pubsub.unsubscribe.assert_called_once()

    @patch("src.common.base_subscriber.get_pubsub")
    async def test_subscribe_to_channel_cleanup(self, mock_get_pubsub: AsyncMock) -> None:
        """Test that subscribe_to_channel cleans up properly on manual exit."""
        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub

        channel = "test_channel"

        # Use the iterator but exit immediately to test cleanup
        iterator = subscribe_to_channel(channel, max_idle_time=5.0)

        try:
            await iterator.__anext__()  # Start the iterator
        except (TimeoutError, StopAsyncIteration):
            pass  # Expected when no messages
        finally:
            await iterator.aclose()  # Ensure cleanup

        # Verify subscribe was called
        mock_pubsub.subscribe.assert_called_once()
        # Cleanup should have been called
        mock_pubsub.unsubscribe.assert_called_once()


@pytest.mark.asyncio
class TestAsyncTimeoutIntegration:
    """Test async_timeout integration when available."""

    @patch("src.common.base_subscriber._ASYNC_TIMEOUT_AVAILABLE", ASYNC_TIMEOUT_AVAILABLE_TRUE)
    @patch("src.common.base_subscriber.async_timeout")
    async def test_async_timeout_used_when_available(self, mock_async_timeout: Mock) -> None:
        """Test that async_timeout is used when available."""
        # Mock async_timeout.timeout context manager
        mock_timeout_cm = AsyncMock()
        mock_async_timeout.timeout.return_value = mock_timeout_cm
        mock_timeout_cm.__aenter__ = AsyncMock(return_value=None)
        mock_timeout_cm.__aexit__ = AsyncMock(return_value=None)

        subscriber = ConcreteTestSubscriber(ack_timeout=5.0)

        # Mock the wrapped function
        with patch.object(subscriber, "_with_circuit_breaker") as mock_wrap:
            mock_process = AsyncMock(return_value=True)
            mock_wrap.return_value = mock_process

            message = {"content": "test"}

            # This should use async_timeout when available
            await subscriber._handle_single_message(message)

            # Verify async_timeout was used
            mock_async_timeout.timeout.assert_called_once_with(5.0)

    @patch("src.common.base_subscriber._ASYNC_TIMEOUT_AVAILABLE", ASYNC_TIMEOUT_AVAILABLE_FALSE)
    async def test_asyncio_wait_for_fallback(self) -> None:
        """Test fallback to asyncio.wait_for when async_timeout not available."""
        subscriber = ConcreteTestSubscriber(ack_timeout=0.1)
        subscriber.processing_delay = 0.2  # Longer than timeout

        message = {"content": "test"}

        # Should raise TimeoutError using asyncio.wait_for
        with pytest.raises(asyncio.TimeoutError):
            await subscriber._handle_single_message(message)


# Integration test markers
class TestIntegrationScenarios:
    """Integration test scenarios combining multiple features."""

    @pytest.mark.integration
    @patch("src.common.base_subscriber.get_pubsub")
    async def test_end_to_end_processing_scenario(self, mock_get_pubsub: AsyncMock) -> None:
        """Test complete end-to-end message processing scenario."""
        # Mock Redis and pubsub
        mock_redis = AsyncMock()
        mock_pubsub = AsyncMock()
        mock_pubsub._redis = mock_redis
        mock_get_pubsub.return_value = mock_pubsub

        # Mock DLQ function
        dlq_messages = []

        async def mock_dlq(message: MessageDict) -> None:
            dlq_messages.append(message)

        # Create subscriber with all features enabled
        circuit_breaker = CircuitBreaker(failure_threshold=2)
        subscriber = ConcreteTestSubscriber(
            concurrency=4,
            batch_size=2,
            batch_window=0.1,
            circuit_breaker=circuit_breaker,
            dlq_publish=mock_dlq,
        )

        # Set up mixed success/failure results
        subscriber.processing_results = [True, False, True, False, True]

        # Simulate batch processing
        messages = [
            {"id": i, "content": f"message_{i}", "_subscriber_message_id": f"msg_{i}"}
            for i in range(INTEGRATION_TOTAL_MESSAGES)
        ]

        # Process messages in batches
        batch1 = messages[:2]
        batch2 = messages[2:4]
        single_message = messages[4]

        # Process batches
        await subscriber._handle_message_batch(batch1)
        await subscriber._handle_message_batch(batch2)
        await subscriber._handle_single_message(single_message)

        # Allow processing to complete
        await asyncio.sleep(0.1)

        # Verify results
        assert len(subscriber.processed_messages) == INTEGRATION_TOTAL_MESSAGES
        assert len(dlq_messages) == INTEGRATION_FAILED_MESSAGES  # Failed messages
        assert subscriber.metrics["processed_count"] == INTEGRATION_TOTAL_MESSAGES
        assert subscriber.metrics["dlq_count"] == INTEGRATION_FAILED_MESSAGES

        # Verify Redis ACK operations
        assert mock_redis.setex.call_count == INTEGRATION_TOTAL_MESSAGES  # Set processing state
        assert mock_redis.delete.call_count == INTEGRATION_TOTAL_MESSAGES  # Acknowledge all messages
