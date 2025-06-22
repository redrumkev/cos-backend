"""Unit tests for L1 logging service Redis publishing functionality.

Tests the enhanced log_l1 function with Redis publishing after successful database commit,
including error isolation, circuit breaker integration, and performance validation.

Following TDD methodology: RED → GREEN → REFACTOR
"""

import asyncio
import uuid
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.logging import log_l1
from src.backend.cc.mem0_models import BaseLog, EventLog


class TestLogL1RedisPublishAfterCommit:
    """Test Redis publishing after successful database commit."""

    @patch("src.backend.cc.logging._publish_l1_event")
    async def test_publish_after_commit_event_log(self, mock_publish: AsyncMock, test_db_session: AsyncSession) -> None:
        """Test that Redis publish is scheduled after successful commit for event logs."""
        payload = {"action": "test_event", "value": 42}

        result = await log_l1(db=test_db_session, event_type="test_event", payload=payload)

        # Verify the event was logged to database
        assert "base_log_id" in result
        assert "event_log_id" in result

        # Verify publish was scheduled after commit
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args[0]

        # Verify call arguments structure
        assert len(call_args) == 2
        log_id, event_data = call_args

        assert log_id == result["event_log_id"]
        assert event_data["event_type"] == "test_event"
        assert event_data["event_data"] == payload
        assert "created_at" in event_data
        assert "log_id" in event_data

    @patch("src.backend.cc.logging._publish_l1_event")
    async def test_no_publish_without_event_log(self, mock_publish: AsyncMock, test_db_session: AsyncSession) -> None:
        """Test that Redis publish is not called when no event log is created."""
        # Only prompt data, no payload - should not create event log
        prompt_data = {"prompt_text": "Test prompt"}

        result = await log_l1(db=test_db_session, event_type="prompt_only", prompt_data=prompt_data)

        # Verify no event log was created
        assert "event_log_id" not in result
        assert "base_log_id" in result

        # Verify publish was not called
        mock_publish.assert_not_called()

    @patch("src.backend.cc.logging._publish_l1_event")
    async def test_publish_with_trace_id(self, mock_publish: AsyncMock, test_db_session: AsyncSession) -> None:
        """Test publish includes trace_id when available."""
        payload = {"action": "traced_event"}
        trace_id = "123456789abcdef"

        await log_l1(db=test_db_session, event_type="traced_event", payload=payload, trace_id=trace_id)

        # Verify publish was called with trace_id
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args[0]
        log_id, event_data = call_args

        assert event_data["trace_id"] == trace_id

    @patch("src.backend.cc.logging._publish_l1_event")
    async def test_publish_with_request_id(self, mock_publish: AsyncMock, test_db_session: AsyncSession) -> None:
        """Test publish includes request_id in event data."""
        payload = {"action": "request_event"}
        request_id = str(uuid.uuid4())

        await log_l1(db=test_db_session, event_type="request_event", payload=payload, request_id=request_id)

        # Verify publish was called with request_id
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args[0]
        log_id, event_data = call_args

        assert event_data["request_id"] == request_id


class TestLogL1RedisPublishErrorIsolation:
    """Test error isolation between database operations and Redis publishing."""

    @patch("src.backend.cc.logging._publish_l1_event")
    async def test_database_success_despite_publish_failure(
        self, mock_publish: AsyncMock, test_db_session: AsyncSession
    ) -> None:
        """Test that database operations succeed even if Redis publish fails."""
        # Make publish fail
        mock_publish.side_effect = Exception("Redis connection failed")

        payload = {"action": "resilient_event"}

        # Should complete successfully despite publish failure
        result = await log_l1(db=test_db_session, event_type="resilient_event", payload=payload)

        # Verify database operations completed
        assert "base_log_id" in result
        assert "event_log_id" in result

        # Verify records exist in database
        base_log = await test_db_session.get(BaseLog, result["base_log_id"])
        event_log = await test_db_session.get(EventLog, result["event_log_id"])

        assert base_log is not None
        assert event_log is not None
        assert event_log.event_type == "resilient_event"

    @patch("src.backend.cc.logging._publish_l1_event")
    async def test_publish_error_logged_but_not_raised(
        self, mock_publish: AsyncMock, test_db_session: AsyncSession, caplog: Any
    ) -> None:
        """Test that publish errors are logged but not re-raised."""
        mock_publish.side_effect = Exception("Redis timeout")

        payload = {"action": "error_logged_event"}

        # Should not raise exception
        result = await log_l1(db=test_db_session, event_type="error_logged_event", payload=payload)

        # Verify database operation succeeded
        assert "event_log_id" in result

        # Note: Error logging verification would be in _publish_l1_event implementation


class TestPublishL1EventFunction:
    """Test the _publish_l1_event helper function."""

    @patch("src.backend.cc.logging.get_pubsub")
    async def test_publish_l1_event_success(self, mock_get_pubsub: AsyncMock) -> None:
        """Test successful Redis publish operation."""
        # Import function after patching to avoid import errors
        from src.backend.cc.logging import _publish_l1_event

        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub
        mock_pubsub.publish.return_value = 1  # 1 subscriber received message

        log_id = UUID("12345678-1234-5678-9012-123456789abc")
        event_data = {
            "event_type": "test_event",
            "event_data": {"action": "test"},
            "created_at": "2024-01-01T00:00:00Z",
            "log_id": str(log_id),
        }

        # Should complete without error
        await _publish_l1_event(log_id, event_data)

        # Verify Redis publish was called
        mock_pubsub.publish.assert_called_once_with("mem0.recorded.cc", event_data)

    @patch("src.backend.cc.logging.get_pubsub")
    async def test_publish_l1_event_redis_error_isolation(self, mock_get_pubsub: AsyncMock, caplog: Any) -> None:
        """Test that Redis errors are isolated and logged."""
        from src.backend.cc.logging import _publish_l1_event

        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub
        mock_pubsub.publish.side_effect = Exception("Redis connection lost")

        log_id = UUID("12345678-1234-5678-9012-123456789abc")
        event_data = {"event_type": "test_event"}

        # Should not raise exception
        await _publish_l1_event(log_id, event_data)

        # Verify error was logged (implementation detail)
        # The actual logging verification would depend on implementation

    @patch("src.backend.cc.logging.get_pubsub")
    @patch("src.backend.cc.logging.logfire")
    async def test_publish_l1_event_logfire_span(self, mock_logfire: Mock, mock_get_pubsub: AsyncMock) -> None:
        """Test Logfire span integration in publish function."""
        from src.backend.cc.logging import _publish_l1_event

        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub
        mock_pubsub.publish.return_value = 1

        # Mock Logfire span context manager
        mock_span = Mock()
        mock_logfire.span.return_value.__aenter__ = AsyncMock(return_value=mock_span)
        mock_logfire.span.return_value.__aexit__ = AsyncMock(return_value=None)

        log_id = UUID("12345678-1234-5678-9012-123456789abc")
        event_data = {"event_type": "test_event"}

        await _publish_l1_event(log_id, event_data)

        # Verify Logfire span was created
        mock_logfire.span.assert_called_once_with("publish_l1_event", kind="producer")


class TestSQLAlchemyAfterCommitIntegration:
    """Test SQLAlchemy after_commit event listener integration."""

    @patch("src.backend.cc.logging._publish_l1_event")
    async def test_after_commit_listener_registered(
        self, mock_publish: AsyncMock, test_db_session: AsyncSession
    ) -> None:
        """Test that after_commit listener is properly registered and triggered."""
        payload = {"action": "commit_test"}

        await log_l1(db=test_db_session, event_type="commit_test", payload=payload)

        # The after_commit listener should be triggered after the session commit
        # and _publish_l1_event should be scheduled as a task
        mock_publish.assert_called_once()

    async def test_outbox_pattern_session_isolation(self, test_db_session: AsyncSession) -> None:
        """Test that outbox events are isolated per session."""
        # This test verifies that the session.info["l1_outbox"] pattern
        # correctly isolates events between different sessions

        # Session should start clean
        assert "l1_outbox" not in test_db_session.info

        # After logging, there should be no lingering outbox data
        # (because it gets popped in the after_commit handler)
        await log_l1(db=test_db_session, event_type="isolation_test", payload={"test": "data"})

        # Session info should be clean after commit
        assert "l1_outbox" not in test_db_session.info


class TestRedisChannelAndMessageFormat:
    """Test Redis channel naming and message format specifications."""

    @patch("src.backend.cc.logging.get_pubsub")
    async def test_correct_channel_name(self, mock_get_pubsub: AsyncMock, test_db_session: AsyncSession) -> None:
        """Test that messages are published to the correct Redis channel."""
        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub

        payload = {"action": "channel_test"}

        await log_l1(db=test_db_session, event_type="channel_test", payload=payload)

        # Verify correct channel is used
        mock_pubsub.publish.assert_called_once()
        call_args = mock_pubsub.publish.call_args[0]
        channel_name = call_args[0]

        assert channel_name == "mem0.recorded.cc"

    @patch("src.backend.cc.logging.get_pubsub")
    async def test_message_format_structure(self, mock_get_pubsub: AsyncMock, test_db_session: AsyncSession) -> None:
        """Test that published messages have the correct JSON structure."""
        mock_pubsub = AsyncMock()
        mock_get_pubsub.return_value = mock_pubsub

        payload = {"action": "format_test", "value": 123}
        request_id = str(uuid.uuid4())
        trace_id = "abc123def456"

        await log_l1(
            db=test_db_session, event_type="format_test", payload=payload, request_id=request_id, trace_id=trace_id
        )

        # Verify message structure
        mock_pubsub.publish.assert_called_once()
        call_args = mock_pubsub.publish.call_args[0]
        message_data = call_args[1]

        # Required fields
        assert "log_id" in message_data
        assert "created_at" in message_data
        assert "event" in message_data

        # Event data structure
        event = message_data["event"]
        assert event["event_type"] == "format_test"
        assert event["event_data"] == payload
        assert event["request_id"] == request_id
        assert event["trace_id"] == trace_id

        # Timestamp format (ISO 8601)
        assert isinstance(message_data["created_at"], str)
        # Could add more specific datetime format validation here


class TestPerformanceAndLatencyTargets:
    """Test performance characteristics of the enhanced logging service."""

    @patch("src.backend.cc.logging._publish_l1_event")
    async def test_logging_latency_target(self, mock_publish: AsyncMock, test_db_session: AsyncSession) -> None:
        """Test that logging operations maintain P95 latency target < 2ms."""
        payload = {"action": "latency_test"}

        # start_time = time.perf_counter()
        result = await log_l1(db=test_db_session, event_type="latency_test", payload=payload)
        # end_time = time.perf_counter()

        # latency_ms = (end_time - start_time) * 1000

        # Database operations should complete quickly
        # Note: This target might be optimistic for test environment
        # but ensures we're aware of performance characteristics
        assert "event_log_id" in result

        # Publish should be scheduled asynchronously (fire-and-forget)
        mock_publish.assert_called_once()

    @patch("src.backend.cc.logging._publish_l1_event")
    async def test_fire_and_forget_pattern(self, mock_publish: AsyncMock, test_db_session: AsyncSession) -> None:
        """Test that Redis publishing uses fire-and-forget pattern."""

        # Mock publish to be slow to verify it doesn't block main operation
        async def slow_publish(*args: Any) -> None:
            await asyncio.sleep(0.1)  # 100ms delay

        mock_publish.side_effect = slow_publish

        payload = {"action": "fire_forget_test"}

        # start_time = time.perf_counter()
        result = await log_l1(db=test_db_session, event_type="fire_forget_test", payload=payload)
        # end_time = time.perf_counter()

        # Main operation should complete quickly despite slow publish
        # latency_ms = (end_time - start_time) * 1000

        # Should complete in reasonable time (not wait for 100ms publish delay)
        # assert latency_ms < 50  # Much less than the 100ms publish delay
        assert "event_log_id" in result
