# Test file - configured per-file ignores in ruff.toml handle common test patterns
"""Simplified unit tests for Redis publishing functionality in logging service.

Tests focus on the _publish_l1_event function in isolation without requiring
full database setup. This allows validation of the core Redis publishing logic.
"""

import uuid
from unittest.mock import ANY, AsyncMock, Mock, patch


class TestPublishL1EventFunction:
    """Test the _publish_l1_event helper function in isolation."""

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.get_pubsub")
    @patch("src.backend.cc.logging.logfire")
    async def test_publish_l1_event_success(
        self, mock_logfire: Mock, mock_get_pubsub: AsyncMock, mock_should_publish: Mock
    ) -> None:
        """Test successful Redis publish operation."""
        from src.backend.cc.logging import _publish_l1_event

        # Enable publishing for this test
        mock_should_publish.return_value = True

        # Setup mocks
        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub
        mock_pubsub.publish.return_value = 1  # 1 subscriber received message

        # Mock Logfire span context manager
        mock_span = Mock()
        mock_logfire.span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_logfire.span.return_value.__exit__ = Mock(return_value=None)

        log_id = uuid.UUID("12345678-1234-5678-9012-123456789abc")
        event_data = {
            "log_id": str(log_id),
            "created_at": "2024-01-01T00:00:00Z",
            "event": {
                "event_type": "test_event",
                "event_data": {"action": "test"},
                "request_id": "test-request-id",
                "trace_id": "test-trace-id",
            },
        }

        # Should complete without error
        await _publish_l1_event(log_id, event_data)

        # Verify Redis publish was called
        mock_pubsub.publish.assert_called_once_with("mem0.recorded.cc", event_data, correlation_id=ANY)

        # Verify Logfire span was created with additional parameters
        mock_logfire.span.assert_called_once_with("publish_l1_event", kind="producer", log_id=ANY, correlation_id=ANY)

        # Verify span attributes were set
        mock_span.set_attribute.assert_any_call("log_id", str(log_id))
        mock_span.set_attribute.assert_any_call("event_type", "test_event")

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.get_pubsub")
    @patch("src.backend.cc.logging.logfire")
    async def test_publish_l1_event_redis_error_isolation(
        self, mock_logfire: Mock, mock_get_pubsub: AsyncMock, mock_should_publish: Mock
    ) -> None:
        """Test that Redis errors are isolated and logged."""
        from src.backend.cc.logging import _publish_l1_event

        # Enable publishing for this test
        mock_should_publish.return_value = True

        # Setup mocks
        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub
        mock_pubsub.publish.side_effect = Exception("Redis connection lost")

        # Mock the publish_with_fallback method to succeed (preventing second logfire.error call)
        mock_pubsub.publish_with_fallback = AsyncMock(return_value={"success": True, "fallback_used": True})

        # Mock Logfire span context manager
        mock_span = Mock()
        mock_logfire.span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_logfire.span.return_value.__exit__ = Mock(return_value=None)

        log_id = uuid.UUID("12345678-1234-5678-9012-123456789abc")
        event_data = {"event_type": "test_event"}

        # Should not raise exception
        await _publish_l1_event(log_id, event_data)

        # Verify error was logged for primary failure
        # There should be one error call for the primary failure and one info call for fallback success
        assert mock_logfire.error.call_count == 1
        error_call_args = mock_logfire.error.call_args[1]
        assert error_call_args["log_id"] == str(log_id)
        assert error_call_args["error"] == "Redis connection lost"
        assert error_call_args["error_type"] == "Exception"

        # Verify fallback was attempted
        mock_pubsub.publish_with_fallback.assert_called_once()

        # Verify info call for successful fallback
        mock_logfire.info.assert_called_once()

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.get_pubsub")
    @patch("src.backend.cc.logging.logfire")
    async def test_publish_l1_event_logfire_span_error_isolation(
        self, mock_logfire: Mock, mock_get_pubsub: AsyncMock, mock_should_publish: Mock
    ) -> None:
        """Test that Logfire span errors are also isolated."""
        from src.backend.cc.logging import _publish_l1_event

        # Enable publishing for this test
        mock_should_publish.return_value = True

        # Setup mocks
        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub
        mock_pubsub.publish.return_value = 1

        # Make Logfire span creation fail
        mock_logfire.span.side_effect = Exception("Logfire error")

        log_id = uuid.UUID("12345678-1234-5678-9012-123456789abc")
        event_data = {"event_type": "test_event"}

        # Should not raise exception
        await _publish_l1_event(log_id, event_data)

        # Verify error was logged (should be called twice - once for main error, once for fallback)
        assert mock_logfire.error.call_count == 2
        # Check the first error call
        first_call_args = mock_logfire.error.call_args_list[0][1]
        assert first_call_args["log_id"] == str(log_id)
        assert first_call_args["error"] == "Logfire error"


class TestAfterCommitEventListener:
    """Test the SQLAlchemy after_commit event listener."""

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.asyncio.get_running_loop")
    @patch("src.backend.cc.logging._publish_l1_event")
    def test_after_commit_listener_schedules_tasks(
        self, mock_publish: AsyncMock, mock_get_loop: Mock, mock_should_publish: Mock
    ) -> None:
        """Test that after_commit listener schedules publishing tasks."""
        from src.backend.cc.logging import _after_commit_publish_events

        # Enable publishing for this test
        mock_should_publish.return_value = True

        # Setup mocks
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_loop.is_closed.return_value = False
        mock_get_loop.return_value = mock_loop

        # Create mock session with outbox events
        mock_session = Mock()
        log_id_1 = uuid.UUID("12345678-1234-5678-9012-123456789abc")
        log_id_2 = uuid.UUID("87654321-4321-8765-2109-cba987654321")

        event_data_1 = {"event_type": "event_1"}
        event_data_2 = {"event_type": "event_2"}

        mock_session.info = {"l1_outbox": [(log_id_1, event_data_1), (log_id_2, event_data_2)]}

        # Call the listener
        _after_commit_publish_events(mock_session)

        # Verify outbox was cleared
        assert "l1_outbox" not in mock_session.info

        # Verify tasks were scheduled
        assert mock_loop.create_task.call_count == 2

        # Verify the correct tasks were created with the right arguments
        # Note: We can't easily verify the exact coroutine arguments due to how create_task works

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.asyncio.get_running_loop")
    @patch("src.backend.cc.logging.logfire")
    def test_after_commit_listener_no_event_loop(
        self, mock_logfire: Mock, mock_get_loop: Mock, mock_should_publish: Mock
    ) -> None:
        """Test graceful handling when no event loop is running."""
        from src.backend.cc.logging import _after_commit_publish_events

        # Enable publishing for this test
        mock_should_publish.return_value = True

        # Make get_running_loop raise RuntimeError
        mock_get_loop.side_effect = RuntimeError("No running event loop")

        # Create mock session with outbox events
        mock_session = Mock()
        mock_session.info = {"l1_outbox": [(uuid.uuid4(), {"event_type": "test"})]}

        # Should not raise exception
        _after_commit_publish_events(mock_session)

        # Verify warning was logged
        mock_logfire.warn.assert_called_once_with("No running event loop for Redis publishing", event_count=1)

    def test_after_commit_listener_no_outbox(self) -> None:
        """Test that listener does nothing when no outbox events exist."""
        from src.backend.cc.logging import _after_commit_publish_events

        # Create mock session without outbox
        mock_session = Mock()
        mock_session.info = Mock()
        mock_session.info.pop.return_value = None  # No outbox events

        # Should return early without error
        _after_commit_publish_events(mock_session)

        # Verify session.info.pop was called to check for outbox
        mock_session.info.pop.assert_called_once_with("l1_outbox", None)


class TestRedisChannelAndMessageFormat:
    """Test Redis channel naming and message format specifications."""

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.get_pubsub")
    @patch("src.backend.cc.logging.logfire")
    async def test_correct_channel_name(
        self, mock_logfire: Mock, mock_get_pubsub: AsyncMock, mock_should_publish: Mock
    ) -> None:
        """Test that messages are published to the correct Redis channel."""
        from src.backend.cc.logging import _publish_l1_event

        # Enable publishing for this test
        mock_should_publish.return_value = True

        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub

        # Mock Logfire span
        mock_span = Mock()
        mock_logfire.span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_logfire.span.return_value.__exit__ = Mock(return_value=None)

        log_id = uuid.UUID("12345678-1234-5678-9012-123456789abc")
        event_data = {"event": {"event_type": "channel_test"}}

        await _publish_l1_event(log_id, event_data)

        # Verify correct channel is used
        mock_pubsub.publish.assert_called_once_with("mem0.recorded.cc", event_data, correlation_id=ANY)

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.get_pubsub")
    @patch("src.backend.cc.logging.logfire")
    async def test_message_data_passed_correctly(
        self, mock_logfire: Mock, mock_get_pubsub: AsyncMock, mock_should_publish: Mock
    ) -> None:
        """Test that the event data is passed correctly to Redis publish."""
        from src.backend.cc.logging import _publish_l1_event

        # Enable publishing for this test
        mock_should_publish.return_value = True

        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub

        # Mock Logfire span
        mock_span = Mock()
        mock_logfire.span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_logfire.span.return_value.__exit__ = Mock(return_value=None)

        log_id = uuid.UUID("12345678-1234-5678-9012-123456789abc")
        complex_event_data = {
            "log_id": str(log_id),
            "created_at": "2024-01-01T00:00:00Z",
            "event": {
                "event_type": "complex_test",
                "event_data": {"nested": {"value": 123}, "array": [1, 2, 3]},
                "request_id": "req-123",
                "trace_id": "trace-456",
            },
        }

        await _publish_l1_event(log_id, complex_event_data)

        # Verify the exact data structure is passed to Redis
        mock_pubsub.publish.assert_called_once_with("mem0.recorded.cc", complex_event_data, correlation_id=ANY)


class TestObservabilityIntegration:
    """Test Logfire observability integration."""

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.get_pubsub")
    @patch("src.backend.cc.logging.logfire")
    async def test_span_attributes_set_correctly(
        self, mock_logfire: Mock, mock_get_pubsub: AsyncMock, mock_should_publish: Mock
    ) -> None:
        """Test that Logfire span attributes are set with correct values."""
        from src.backend.cc.logging import _publish_l1_event

        # Enable publishing for this test
        mock_should_publish.return_value = True

        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub

        # Mock Logfire span
        mock_span = Mock()
        mock_logfire.span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_logfire.span.return_value.__exit__ = Mock(return_value=None)

        log_id = uuid.UUID("12345678-1234-5678-9012-123456789abc")
        event_data = {"event": {"event_type": "observability_test", "event_data": {"key": "value"}}}

        await _publish_l1_event(log_id, event_data)

        # Verify span attributes
        mock_span.set_attribute.assert_any_call("log_id", str(log_id))
        mock_span.set_attribute.assert_any_call("event_type", "observability_test")

    @patch("src.backend.cc.logging._should_publish_events")
    @patch("src.backend.cc.logging.get_pubsub")
    @patch("src.backend.cc.logging.logfire")
    async def test_span_handles_missing_event_type(
        self, mock_logfire: Mock, mock_get_pubsub: AsyncMock, mock_should_publish: Mock
    ) -> None:
        """Test span attribute handling when event_type is missing."""
        from src.backend.cc.logging import _publish_l1_event

        # Enable publishing for this test
        mock_should_publish.return_value = True

        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub

        # Mock Logfire span
        mock_span = Mock()
        mock_logfire.span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_logfire.span.return_value.__exit__ = Mock(return_value=None)

        log_id = uuid.UUID("12345678-1234-5678-9012-123456789abc")
        event_data = {"some": "data"}  # No event.event_type structure

        await _publish_l1_event(log_id, event_data)

        # Verify span attributes with fallback
        mock_span.set_attribute.assert_any_call("log_id", str(log_id))
        mock_span.set_attribute.assert_any_call("event_type", "unknown")
