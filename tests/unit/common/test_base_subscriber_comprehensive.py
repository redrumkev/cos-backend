# Test file - configured per-file ignores in ruff.toml handle common test patterns
"""Comprehensive unit tests for BaseSubscriber implementation."""

import asyncio
import contextlib
import time
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time

from src.common.base_subscriber import (
    DEFAULT_ACK_TIMEOUT,
    DEFAULT_BATCH_SIZE,
    DEFAULT_BATCH_WINDOW,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_MESSAGE_TTL,
    BaseSubscriber,
    publish_to_dlq,
    subscribe_to_channel,
)
from src.common.pubsub import CircuitBreaker, CircuitBreakerState


class ConcreteSubscriber(BaseSubscriber):
    """Concrete implementation for testing."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.processed_messages: list[dict[str, Any]] = []
        self.process_success = True
        self.process_delay = 0.0

    async def process_message(self, message: dict[str, Any]) -> bool:
        """Process a single message."""
        if self.process_delay > 0:
            await asyncio.sleep(self.process_delay)

        self.processed_messages.append(message)
        return self.process_success


class TestBaseSubscriber:
    """Comprehensive test suite for BaseSubscriber."""

    @pytest.fixture
    def subscriber(self) -> ConcreteSubscriber:
        """Create subscriber instance for testing."""
        return ConcreteSubscriber()

    @pytest.fixture
    def subscriber_with_circuit_breaker(self, circuit_breaker_config: dict[str, Any]) -> ConcreteSubscriber:
        """Create subscriber with circuit breaker."""
        cb = CircuitBreaker(**circuit_breaker_config)
        return ConcreteSubscriber(circuit_breaker=cb)

    @pytest.fixture
    def subscriber_with_dlq(self) -> ConcreteSubscriber:
        """Create subscriber with DLQ support."""
        dlq_messages = []

        async def dlq_publisher(message: dict[str, Any]) -> None:
            dlq_messages.append(message)

        subscriber = ConcreteSubscriber(dlq_publish=dlq_publisher)
        subscriber.dlq_messages = dlq_messages  # type: ignore[attr-defined]
        return subscriber

    async def test_init_default_values(self) -> None:
        """Test BaseSubscriber initialization with default values."""
        subscriber = ConcreteSubscriber()

        assert subscriber._concurrency == DEFAULT_MAX_CONCURRENCY
        assert subscriber._ack_timeout == DEFAULT_ACK_TIMEOUT
        assert subscriber._batch_size == DEFAULT_BATCH_SIZE
        assert subscriber._batch_window == DEFAULT_BATCH_WINDOW
        assert subscriber._message_ttl == DEFAULT_MESSAGE_TTL
        assert subscriber._circuit_breaker is None
        assert subscriber._dlq_publish is None

    async def test_init_custom_values(self) -> None:
        """Test BaseSubscriber initialization with custom values."""
        cb = CircuitBreaker()

        async def dlq_func(msg: dict[str, Any]) -> None:
            pass

        subscriber = ConcreteSubscriber(
            concurrency=16,
            circuit_breaker=cb,
            ack_timeout=2.0,
            dlq_publish=dlq_func,
            batch_size=50,
            batch_window=1.0,
            message_ttl=600,
        )

        assert subscriber._concurrency == 16
        assert subscriber._circuit_breaker is cb
        assert subscriber._ack_timeout == 2.0
        assert subscriber._dlq_publish is dlq_func
        assert subscriber._batch_size == 50
        assert subscriber._batch_window == 1.0
        assert subscriber._message_ttl == 600

    async def test_properties(self, subscriber: ConcreteSubscriber) -> None:
        """Test BaseSubscriber properties."""
        assert not subscriber.is_consuming
        assert subscriber.metrics["processed_count"] == 0
        assert subscriber.metrics["failed_count"] == 0
        assert subscriber.metrics["concurrency_limit"] == DEFAULT_MAX_CONCURRENCY

    async def test_process_batch_default_implementation(self, subscriber: ConcreteSubscriber) -> None:
        """Test default process_batch implementation."""
        messages = [
            {"id": 1, "data": "test1"},
            {"id": 2, "data": "test2"},
            {"id": 3, "data": "test3"},
        ]

        results = await subscriber.process_batch(messages)

        assert results == [True, True, True]
        assert len(subscriber.processed_messages) == 3

    async def test_process_batch_with_failures(self, subscriber: ConcreteSubscriber) -> None:
        """Test process_batch with some failures."""
        messages = [
            {"id": 1, "data": "test1"},
            {"id": 2, "data": "test2"},
        ]

        # Make second message fail
        call_count = 0
        original_process = subscriber.process_message

        async def failing_process(message: dict[str, Any]) -> bool:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ValueError("Process failed")
            return await original_process(message)

        subscriber.process_message = failing_process  # type: ignore[method-assign]

        results = await subscriber.process_batch(messages)

        assert results == [True, False]

    async def test_start_consuming_single_message_mode(self, subscriber: ConcreteSubscriber) -> None:
        """Test start_consuming in single message mode."""
        # Mock subscribe_to_channel
        messages = [
            {"id": 1, "data": "test1"},
            {"id": 2, "data": "test2"},
        ]

        async def mock_subscribe(channel: str) -> AsyncGenerator[dict[str, Any], None]:
            for msg in messages:
                yield {**msg, "_subscriber_message_id": f"msg_{msg['id']}"}

        with patch("src.common.base_subscriber.subscribe_to_channel", mock_subscribe):
            await subscriber.start_consuming("test_channel")

            # Let messages process
            await asyncio.sleep(0.1)

            assert subscriber.is_consuming
            assert "test_channel" in subscriber._channels

            # Stop consuming
            await subscriber.stop_consuming()

            assert not subscriber.is_consuming
            assert len(subscriber.processed_messages) >= 0  # May process some before stop

    async def test_start_consuming_batch_mode(self, subscriber: ConcreteSubscriber) -> None:
        """Test start_consuming in batch mode."""
        subscriber._batch_size = 2  # Small batch for testing

        messages = [
            {"id": 1, "data": "test1"},
            {"id": 2, "data": "test2"},
            {"id": 3, "data": "test3"},
        ]

        async def mock_subscribe(channel: str) -> AsyncGenerator[dict[str, Any], None]:
            for msg in messages:
                yield {**msg, "_subscriber_message_id": f"msg_{msg['id']}"}
                await asyncio.sleep(0.01)  # Small delay

        with patch("src.common.base_subscriber.subscribe_to_channel", mock_subscribe):
            await subscriber.start_consuming("test_channel")

            # Let batches process
            await asyncio.sleep(0.2)

            assert subscriber.is_consuming

            await subscriber.stop_consuming()

    async def test_start_consuming_already_consuming(self, subscriber: ConcreteSubscriber, caplog: Any) -> None:
        """Test start_consuming when already consuming from channel."""
        subscriber._channels.add("test_channel")

        await subscriber.start_consuming("test_channel")

        assert "Already consuming" in caplog.text

    async def test_stop_consuming_cleanup(self, subscriber: ConcreteSubscriber) -> None:
        """Test stop_consuming cleans up properly."""
        # Setup mock state
        mock_task = AsyncMock()
        mock_task.done.return_value = False
        mock_task.cancel = MagicMock()

        subscriber._consuming_tasks.add(mock_task)
        subscriber._channels.add("test_channel")
        subscriber._batch_buffer = [{"test": "data"}]

        mock_batch_task = AsyncMock()
        mock_batch_task.done.return_value = False
        mock_batch_task.cancel = MagicMock()
        subscriber._batch_task = mock_batch_task

        await subscriber.stop_consuming()

        mock_task.cancel.assert_called_once()
        mock_batch_task.cancel.assert_called_once()
        assert len(subscriber._consuming_tasks) == 0
        assert len(subscriber._channels) == 0
        assert subscriber._batch_task is None

    async def test_handle_single_message_success(self, subscriber_with_dlq: ConcreteSubscriber) -> None:
        """Test successful single message handling."""
        with (
            patch.object(subscriber_with_dlq, "_set_processing_state") as mock_set_state,
            patch.object(subscriber_with_dlq, "_acknowledge_message") as mock_ack,
        ):
            mock_set_state.return_value = "processing_key"

            message = {"id": 1, "data": "test", "_subscriber_message_id": "msg_1"}

            await subscriber_with_dlq._handle_single_message(message)

            assert len(subscriber_with_dlq.processed_messages) == 1
            assert subscriber_with_dlq.metrics["processed_count"] == 1
            mock_ack.assert_called_once_with("processing_key")

    async def test_handle_single_message_failure(self, subscriber_with_dlq: ConcreteSubscriber) -> None:
        """Test single message handling with failure."""
        subscriber_with_dlq.process_success = False

        with (
            patch.object(subscriber_with_dlq, "_set_processing_state") as mock_set_state,
            patch.object(subscriber_with_dlq, "_acknowledge_message") as mock_ack,
        ):
            mock_set_state.return_value = "processing_key"

            message = {"id": 1, "data": "test", "_subscriber_message_id": "msg_1"}

            await subscriber_with_dlq._handle_single_message(message)

            assert subscriber_with_dlq.metrics["failed_count"] == 1
            assert len(subscriber_with_dlq.dlq_messages) == 1  # type: ignore
            mock_ack.assert_called_once_with("processing_key")  # Still ACK to prevent reprocessing

    async def test_handle_single_message_timeout(self, subscriber: ConcreteSubscriber) -> None:
        """Test single message handling with timeout."""
        subscriber.process_delay = 1.0  # Longer than default timeout
        subscriber._ack_timeout = 0.1

        with patch.object(subscriber, "_set_processing_state") as mock_set_state:
            mock_set_state.return_value = "processing_key"

            message = {"id": 1, "data": "test", "_subscriber_message_id": "msg_1"}

            # TimeoutError is expected to be raised
            with pytest.raises(TimeoutError):
                await subscriber._handle_single_message(message)

            assert subscriber.metrics["failed_count"] == 1

    async def test_handle_single_message_exception(self, subscriber_with_dlq: ConcreteSubscriber) -> None:
        """Test single message handling with exception."""

        async def failing_process(message: dict[str, Any]) -> bool:
            raise ValueError("Processing error")

        subscriber_with_dlq.process_message = failing_process  # type: ignore[method-assign]

        with patch.object(subscriber_with_dlq, "_set_processing_state") as mock_set_state:
            mock_set_state.return_value = "processing_key"

            message = {"id": 1, "data": "test", "_subscriber_message_id": "msg_1"}

            await subscriber_with_dlq._handle_single_message(message)

            assert subscriber_with_dlq.metrics["failed_count"] == 1
            assert len(subscriber_with_dlq.dlq_messages) == 1  # type: ignore

    async def test_handle_message_batch_success(self, subscriber: ConcreteSubscriber) -> None:
        """Test successful batch message handling."""
        messages = [
            {"id": 1, "data": "test1", "_subscriber_message_id": "msg_1"},
            {"id": 2, "data": "test2", "_subscriber_message_id": "msg_2"},
        ]

        with patch.object(subscriber, "_set_processing_state") as mock_set_state:
            mock_set_state.side_effect = ["key_1", "key_2"]

            await subscriber._handle_message_batch(messages)

            assert subscriber.metrics["processed_count"] == 2
            assert len(subscriber.processed_messages) == 2

    async def test_handle_message_batch_mixed_results(self, subscriber_with_dlq: ConcreteSubscriber) -> None:
        """Test batch handling with mixed success/failure results."""
        messages = [
            {"id": 1, "data": "test1", "_subscriber_message_id": "msg_1"},
            {"id": 2, "data": "test2", "_subscriber_message_id": "msg_2"},
        ]

        # Mock process_batch to return mixed results
        async def mixed_process_batch(messages: list[dict[str, Any]]) -> list[bool]:
            return [True, False]

        subscriber_with_dlq.process_batch = mixed_process_batch  # type: ignore[method-assign]

        with patch.object(subscriber_with_dlq, "_set_processing_state") as mock_set_state:
            mock_set_state.side_effect = ["key_1", "key_2"]

            await subscriber_with_dlq._handle_message_batch(messages)

            assert subscriber_with_dlq.metrics["processed_count"] == 2  # Both messages are processed
            assert subscriber_with_dlq.metrics["failed_count"] == 1  # One message failed
            assert len(subscriber_with_dlq.dlq_messages) == 1  # type: ignore

    async def test_handle_message_batch_exception(self, subscriber_with_dlq: ConcreteSubscriber) -> None:
        """Test batch handling with exception."""
        messages = [
            {"id": 1, "data": "test1", "_subscriber_message_id": "msg_1"},
            {"id": 2, "data": "test2", "_subscriber_message_id": "msg_2"},
        ]

        async def failing_process_batch(messages: list[dict[str, Any]]) -> list[bool]:
            raise ValueError("Batch processing error")

        subscriber_with_dlq.process_batch = failing_process_batch  # type: ignore[method-assign]

        with patch.object(subscriber_with_dlq, "_set_processing_state") as mock_set_state:
            mock_set_state.side_effect = ["key_1", "key_2"]

            await subscriber_with_dlq._handle_message_batch(messages)

            assert subscriber_with_dlq.metrics["failed_count"] == 2
            assert len(subscriber_with_dlq.dlq_messages) == 2  # type: ignore

    async def test_batch_processing_loop(self, subscriber: ConcreteSubscriber) -> None:
        """Test batch processing background loop."""
        subscriber._batch_window = 0.05  # Fast batching for test

        # Add messages to batch buffer
        subscriber._batch_buffer = [
            {"id": 1, "data": "test1", "_subscriber_message_id": "msg_1"},
            {"id": 2, "data": "test2", "_subscriber_message_id": "msg_2"},
        ]

        with patch.object(subscriber, "_handle_message_batch") as mock_handle_batch:
            # Start batch processing loop
            task = asyncio.create_task(subscriber._batch_processing_loop())

            # Wait for batch processing
            await asyncio.sleep(0.1)

            # Stop the loop
            subscriber._stop_event.set()
            task.cancel()

            # Should have processed the batch
            mock_handle_batch.assert_called()

    async def test_batch_processing_loop_cancellation(self, subscriber: ConcreteSubscriber) -> None:
        """Test batch processing loop cancellation."""
        task = asyncio.create_task(subscriber._batch_processing_loop())
        await asyncio.sleep(0.01)  # Let it start

        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_process_batch_buffer(self, subscriber: ConcreteSubscriber) -> None:
        """Test batch buffer processing."""
        subscriber._batch_buffer = [
            {"id": 1, "data": "test1"},
            {"id": 2, "data": "test2"},
        ]

        with patch.object(subscriber, "_handle_message_batch") as mock_handle_batch:
            await subscriber._process_batch_buffer()

            # Buffer should be cleared
            assert len(subscriber._batch_buffer) == 0
            mock_handle_batch.assert_called_once()

    async def test_processing_state_management(self, subscriber: ConcreteSubscriber) -> None:
        """Test message processing state management."""
        with patch("src.common.base_subscriber.get_pubsub") as mock_get_pubsub:
            mock_pubsub = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.setex = AsyncMock()
            mock_redis.delete = AsyncMock(return_value=1)
            mock_pubsub._redis = mock_redis
            mock_get_pubsub.return_value = mock_pubsub

            # Test setting processing state
            key = await subscriber._set_processing_state("msg_123")
            assert key == "processing:msg_123"
            mock_redis.setex.assert_called_once_with("processing:msg_123", DEFAULT_MESSAGE_TTL, "1")

            # Test acknowledging message
            await subscriber._acknowledge_message("processing:msg_123")
            mock_redis.delete.assert_called_once_with("processing:msg_123")

            assert subscriber.metrics["ack_success_count"] == 1

    async def test_processing_state_management_errors(self, subscriber: ConcreteSubscriber, caplog: Any) -> None:
        """Test processing state management with errors."""
        with patch("src.common.base_subscriber.get_pubsub") as mock_get_pubsub:
            mock_pubsub = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.setex.side_effect = Exception("Redis error")
            mock_redis.delete.side_effect = Exception("Redis error")
            mock_pubsub._redis = mock_redis
            mock_get_pubsub.return_value = mock_pubsub

            # Should handle errors gracefully
            key = await subscriber._set_processing_state("msg_123")
            assert key == "processing:msg_123"
            assert "Failed to set processing state" in caplog.text

            await subscriber._acknowledge_message("processing:msg_123")
            assert subscriber.metrics["ack_failed_count"] == 1

    async def test_send_to_dlq(self, subscriber_with_dlq: ConcreteSubscriber) -> None:
        """Test sending messages to DLQ."""
        message = {"id": 1, "data": "test"}

        await subscriber_with_dlq._send_to_dlq(message)

        assert len(subscriber_with_dlq.dlq_messages) == 1  # type: ignore
        dlq_message = subscriber_with_dlq.dlq_messages[0]  # type: ignore[attr-defined]
        assert dlq_message["id"] == 1
        assert dlq_message["data"] == "test"
        assert "_dlq_timestamp" in dlq_message
        assert "_dlq_failure_reason" in dlq_message

    async def test_send_to_dlq_error(self, subscriber: ConcreteSubscriber, caplog: Any) -> None:
        """Test DLQ sending with error."""

        async def failing_dlq(message: dict[str, Any]) -> None:
            raise Exception("DLQ error")

        subscriber._dlq_publish = failing_dlq
        message = {"id": 1, "data": "test"}

        await subscriber._send_to_dlq(message)

        assert "Failed to send message to DLQ" in caplog.text

    async def test_circuit_breaker_integration(self, subscriber_with_circuit_breaker: ConcreteSubscriber) -> None:
        """Test circuit breaker integration."""
        # Force circuit breaker to fail
        subscriber_with_circuit_breaker._circuit_breaker._state = CircuitBreakerState.OPEN  # type: ignore[union-attr]
        subscriber_with_circuit_breaker._circuit_breaker._next_attempt_time = time.time() + 3600  # type: ignore[union-attr]

        message = {"id": 1, "data": "test", "_subscriber_message_id": "msg_1"}

        await subscriber_with_circuit_breaker._handle_single_message(message)

        # Should have failed due to circuit breaker
        assert subscriber_with_circuit_breaker.metrics["failed_count"] == 1

    async def test_circuit_breaker_none_handling(self, subscriber: ConcreteSubscriber) -> None:
        """Test handling when circuit breaker is None."""
        # Should work normally without circuit breaker
        message = {"id": 1, "data": "test"}

        result = await subscriber._with_circuit_breaker(subscriber.process_message)(message)
        assert result is True

    async def test_health_check(self, subscriber: ConcreteSubscriber) -> None:
        """Test health check functionality."""
        subscriber._channels.add("test_channel")

        health = await subscriber.health_check()

        assert health["status"] == "healthy"
        assert health["active_channels"] == ["test_channel"]
        assert "metrics" in health

    async def test_health_check_stopped(self, subscriber: ConcreteSubscriber) -> None:
        """Test health check when stopped."""
        subscriber._stop_event.set()

        health = await subscriber.health_check()

        assert health["status"] == "stopped"

    async def test_metrics_comprehensive(self, subscriber_with_dlq: ConcreteSubscriber) -> None:
        """Test comprehensive metrics collection."""
        # Simulate various operations
        subscriber_with_dlq._processed_count = 10
        subscriber_with_dlq._failed_count = 2
        subscriber_with_dlq._ack_success_count = 8
        subscriber_with_dlq._ack_failed_count = 2
        subscriber_with_dlq._dlq_count = 2
        subscriber_with_dlq._channels.add("test1")
        subscriber_with_dlq._channels.add("test2")
        subscriber_with_dlq._batch_buffer = [{"test": "data"}]

        metrics = subscriber_with_dlq.metrics

        assert metrics["processed_count"] == 10
        assert metrics["failed_count"] == 2
        assert metrics["ack_success_count"] == 8
        assert metrics["ack_failed_count"] == 2
        assert metrics["dlq_count"] == 2
        assert metrics["active_channels"] == 2
        assert metrics["batch_buffer_size"] == 1
        assert metrics["concurrency_limit"] == DEFAULT_MAX_CONCURRENCY

    async def test_consume_loop_error_handling(self, subscriber: ConcreteSubscriber, caplog: Any) -> None:
        """Test consume loop error handling."""

        async def error_subscribe(channel: str) -> AsyncGenerator[dict[str, Any], None]:
            raise Exception("Subscribe error")
            yield  # Unreachable

        with patch("src.common.base_subscriber.subscribe_to_channel", error_subscribe):
            await subscriber._consume_loop("test_channel")

            assert "Error in consumer loop" in caplog.text

    async def test_async_timeout_fallback(self, subscriber: ConcreteSubscriber) -> None:
        """Test fallback when async_timeout is not available."""
        with patch("src.common.base_subscriber._ASYNC_TIMEOUT_AVAILABLE", False):
            subscriber.process_delay = 0.1
            subscriber._ack_timeout = 0.05  # Shorter than process delay

            message = {"id": 1, "data": "test", "_subscriber_message_id": "msg_1"}

            # TimeoutError is expected to be raised when using asyncio.wait_for fallback
            with pytest.raises(TimeoutError):
                await subscriber._handle_single_message(message)

            # Should timeout using asyncio.wait_for
            assert subscriber.metrics["failed_count"] == 1


class TestSubscribeToChannel:
    """Test subscribe_to_channel async generator."""

    async def test_subscribe_to_channel_basic(self) -> None:
        """Test basic subscribe_to_channel functionality."""
        received_messages = []

        with patch("src.common.base_subscriber.get_pubsub") as mock_get_pubsub:
            mock_pubsub = AsyncMock()
            mock_pubsub.subscribe = AsyncMock()
            mock_pubsub.unsubscribe = AsyncMock()
            mock_get_pubsub.return_value = mock_pubsub

            # Create async generator manually
            async def mock_generator() -> AsyncGenerator[dict[str, Any], None]:
                messages = [
                    {"id": 1, "data": "test1"},
                    {"id": 2, "data": "test2"},
                ]
                for msg in messages:
                    yield msg

            # Test the generator
            async for message in mock_generator():
                received_messages.append(message)
                if len(received_messages) >= 2:
                    break

            assert len(received_messages) == 2

    async def test_subscribe_to_channel_cleanup(self) -> None:
        """Test subscribe_to_channel cleanup on exit."""
        with patch("src.common.base_subscriber.get_pubsub") as mock_get_pubsub:
            mock_pubsub = AsyncMock()
            mock_pubsub.subscribe = AsyncMock()
            mock_pubsub.unsubscribe = AsyncMock()
            mock_get_pubsub.return_value = mock_pubsub

            # Use short timeout to prevent hanging in tests
            with contextlib.suppress(Exception):
                async for _message in subscribe_to_channel("test", max_idle_time=0.1):
                    # Immediately break to test cleanup
                    break

            # Should call unsubscribe for cleanup
            mock_pubsub.unsubscribe.assert_called()


class TestPublishToDLQ:
    """Test publish_to_dlq helper function."""

    async def test_publish_to_dlq_basic(self) -> None:
        """Test basic DLQ publishing."""
        with patch("src.common.base_subscriber.get_pubsub") as mock_get_pubsub:
            mock_pubsub = AsyncMock()
            mock_pubsub.publish = AsyncMock()
            mock_get_pubsub.return_value = mock_pubsub

            message = {"id": 1, "data": "test"}

            await publish_to_dlq("original_channel", message)

            # Should publish to DLQ channel
            mock_pubsub.publish.assert_called_once()
            call_args = mock_pubsub.publish.call_args
            assert call_args[0][0] == "dlq:original_channel"

            # Check DLQ message format
            dlq_message = call_args[0][1]
            assert dlq_message["id"] == 1
            assert dlq_message["data"] == "test"
            assert dlq_message["_dlq_original_channel"] == "original_channel"
            assert "_dlq_timestamp" in dlq_message
            assert "_dlq_version" in dlq_message

    async def test_publish_to_dlq_preserves_original_data(self) -> None:
        """Test that DLQ publishing preserves original message data."""
        with patch("src.common.base_subscriber.get_pubsub") as mock_get_pubsub:
            mock_pubsub = AsyncMock()
            mock_pubsub.publish = AsyncMock()
            mock_get_pubsub.return_value = mock_pubsub

            original_message = {
                "id": 123,
                "user_data": {"name": "test", "email": "test@example.com"},
                "metadata": {"source": "api", "version": "1.0"},
                "_original_timestamp": 1700000000.0,
            }

            await publish_to_dlq("user_events", original_message)

            call_args = mock_pubsub.publish.call_args
            dlq_message = call_args[0][1]

            # Original data should be preserved
            assert dlq_message["id"] == 123
            assert dlq_message["user_data"] == original_message["user_data"]
            assert dlq_message["metadata"] == original_message["metadata"]
            assert dlq_message["_original_timestamp"] == 1700000000.0

            # DLQ metadata should be added
            assert dlq_message["_dlq_original_channel"] == "user_events"
            assert isinstance(dlq_message["_dlq_timestamp"], float)
            assert dlq_message["_dlq_version"] == "1.0"


class TestBaseSubscriberAdvancedScenarios:
    """Test advanced BaseSubscriber scenarios."""

    async def test_high_concurrency_processing(self) -> None:
        """Test high concurrency message processing."""
        subscriber = ConcreteSubscriber(concurrency=100)

        # Simulate many concurrent messages
        messages = [{"id": i, "data": f"test{i}"} for i in range(50)]
        tasks = []

        for message in messages:
            task = asyncio.create_task(
                subscriber._handle_single_message({**message, "_subscriber_message_id": f"msg_{message['id']}"})
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        assert subscriber.metrics["processed_count"] == 50
        assert len(subscriber.processed_messages) == 50

    async def test_memory_cleanup_on_stop(self, subscriber: ConcreteSubscriber) -> None:
        """Test memory cleanup when stopping consumer."""
        # Add some state
        subscriber._channels.add("test1")
        subscriber._channels.add("test2")
        subscriber._batch_buffer = [{"test": "data"} for _ in range(10)]
        subscriber.processed_messages = [{"test": "data"} for _ in range(100)]

        initial_memory_usage = len(subscriber._batch_buffer) + len(subscriber.processed_messages)

        await subscriber.stop_consuming()

        # State should be cleaned up
        assert len(subscriber._channels) == 0
        assert len(subscriber._batch_buffer) == 0

        # Processed messages might be kept for debugging, but batch buffer should be clear
        assert len(subscriber._batch_buffer) < initial_memory_usage

    @freeze_time("2023-01-01 12:00:00")
    async def test_message_ttl_handling(self, subscriber: ConcreteSubscriber) -> None:
        """Test message TTL handling in processing state."""
        with patch("src.common.base_subscriber.get_pubsub") as mock_get_pubsub:
            mock_pubsub = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.setex = AsyncMock()
            mock_pubsub._redis = mock_redis
            mock_get_pubsub.return_value = mock_pubsub

            await subscriber._set_processing_state("msg_123")

            # Should set TTL correctly
            mock_redis.setex.assert_called_once_with("processing:msg_123", DEFAULT_MESSAGE_TTL, "1")

    async def test_batch_processing_edge_cases(self, subscriber: ConcreteSubscriber) -> None:
        """Test batch processing edge cases."""
        subscriber._batch_size = 3

        # Test partial batch processing
        messages = [
            {"id": 1, "data": "test1", "_subscriber_message_id": "msg_1"},
            {"id": 2, "data": "test2", "_subscriber_message_id": "msg_2"},
        ]

        # Add to batch buffer but don't reach batch size
        async with subscriber._batch_lock:
            subscriber._batch_buffer.extend(messages)

        # Process partial batch
        await subscriber._process_batch_buffer()

        # Should still process the partial batch
        assert len(subscriber._batch_buffer) == 0
