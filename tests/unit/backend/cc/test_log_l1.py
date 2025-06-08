"""Unit tests for log_l1 async service function.

Focused tests for the log_l1 service function including:
- Basic functionality with different parameter combinations
- Return value structure verification
- Database record creation validation
- Error handling and graceful degradation

Following Task 013 proven testing patterns with realistic expectations.
"""

import uuid
from unittest.mock import Mock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.logging import log_l1
from src.backend.cc.mem0_models import BaseLog, EventLog, PromptTrace


class TestLogL1BasicFunctionality:
    """Test core log_l1 function behavior."""

    async def test_event_only_logging(self, test_db_session: AsyncSession) -> None:
        """Test logging with only event_type and payload."""
        payload = {"action": "test", "value": 42}

        result = await log_l1(db=test_db_session, event_type="test_event", payload=payload)

        # Verify return structure
        assert "base_log_id" in result
        assert "event_log_id" in result
        assert "prompt_trace_id" not in result  # Only created when prompt_data provided

        # Verify database records
        base_log = await test_db_session.get(BaseLog, result["base_log_id"])
        event_log = await test_db_session.get(EventLog, result["event_log_id"])

        assert base_log is not None
        assert event_log is not None
        assert base_log.level == "INFO"
        assert base_log.message == "Event: test_event"
        assert base_log.payload == payload
        assert event_log.event_type == "test_event"
        assert event_log.event_data == payload

    async def test_prompt_only_logging(self, test_db_session: AsyncSession) -> None:
        """Test logging with only prompt_data."""
        prompt_data = {
            "prompt_text": "Test prompt",
            "response_text": "Test response",
            "execution_time_ms": 100,
            "token_count": 50,
        }

        result = await log_l1(db=test_db_session, event_type="prompt_test", prompt_data=prompt_data)

        # Verify return structure
        assert "base_log_id" in result
        assert "prompt_trace_id" in result
        assert "event_log_id" not in result  # Only created when payload provided

        # Verify database records
        base_log = await test_db_session.get(BaseLog, result["base_log_id"])
        prompt_trace = await test_db_session.get(PromptTrace, result["prompt_trace_id"])

        assert base_log is not None
        assert prompt_trace is not None
        assert prompt_trace.prompt_text == "Test prompt"
        assert prompt_trace.response_text == "Test response"
        assert prompt_trace.execution_time_ms == 100
        assert prompt_trace.token_count == 50

    async def test_combined_logging(self, test_db_session: AsyncSession) -> None:
        """Test logging with both payload and prompt_data."""
        payload = {"event": "combined_test"}
        prompt_data = {"prompt_text": "Combined prompt"}

        result = await log_l1(db=test_db_session, event_type="combined_test", payload=payload, prompt_data=prompt_data)

        # Should create all record types
        assert "base_log_id" in result
        assert "event_log_id" in result
        assert "prompt_trace_id" in result

        # Verify all records exist and are linked
        base_log = await test_db_session.get(BaseLog, result["base_log_id"])
        event_log = await test_db_session.get(EventLog, result["event_log_id"])
        prompt_trace = await test_db_session.get(PromptTrace, result["prompt_trace_id"])

        assert base_log is not None
        assert event_log is not None
        assert prompt_trace is not None
        assert event_log.base_log_id == result["base_log_id"]
        assert prompt_trace.base_log_id == result["base_log_id"]

    async def test_minimal_logging(self, test_db_session: AsyncSession) -> None:
        """Test logging with only event_type (no payload or prompt_data)."""
        result = await log_l1(db=test_db_session, event_type="minimal_test")

        # Should only create base_log
        assert "base_log_id" in result
        assert "event_log_id" not in result
        assert "prompt_trace_id" not in result

        # Verify base_log exists
        base_log = await test_db_session.get(BaseLog, result["base_log_id"])
        assert base_log is not None
        assert base_log.message == "Event: minimal_test"


class TestLogL1RequestIdHandling:
    """Test request ID handling behavior."""

    @patch("src.backend.cc.logging.get_request_id")
    async def test_request_id_from_context(self, mock_get_request_id: Mock, test_db_session: AsyncSession) -> None:
        """Test retrieving request ID from context."""
        context_request_id = str(uuid.uuid4())  # Use valid UUID string
        mock_get_request_id.return_value = context_request_id

        result = await log_l1(db=test_db_session, event_type="context_test", payload={"test": "data"})

        # Verify request ID was retrieved from context
        mock_get_request_id.assert_called_once()

        # Verify it was used in the log
        event_log = await test_db_session.get(EventLog, result["event_log_id"])
        assert event_log is not None
        assert str(event_log.request_id) == context_request_id

    @patch("src.backend.cc.logging.get_request_id")
    async def test_request_id_fallback(self, mock_get_request_id: Mock, test_db_session: AsyncSession) -> None:
        """Test UUID fallback when context is empty."""
        mock_get_request_id.return_value = None

        result = await log_l1(db=test_db_session, event_type="fallback_test", payload={"test": "data"})

        # Should generate a UUID fallback
        event_log = await test_db_session.get(EventLog, result["event_log_id"])
        assert event_log is not None
        assert event_log.request_id is not None
        assert isinstance(event_log.request_id, uuid.UUID)

    async def test_explicit_request_id(self, test_db_session: AsyncSession) -> None:
        """Test that explicit request_id parameter is used."""
        explicit_request_id = str(uuid.uuid4())  # Use valid UUID string

        result = await log_l1(
            db=test_db_session, event_type="override_test", payload={"test": "data"}, request_id=explicit_request_id
        )

        # Should use explicit request ID
        event_log = await test_db_session.get(EventLog, result["event_log_id"])
        assert event_log is not None
        assert str(event_log.request_id) == explicit_request_id


class TestLogL1LogfireIntegration:
    """Test Logfire integration patterns."""

    @patch("src.backend.cc.logging.logfire")
    async def test_logfire_span_attributes(self, mock_logfire: Mock, test_db_session: AsyncSession) -> None:
        """Test Logfire span attribute setting."""
        mock_span = Mock()
        mock_logfire.current_span.return_value = mock_span

        result = await log_l1(db=test_db_session, event_type="logfire_test", payload={"test": "data"})

        # Verify span attributes were set
        mock_span.set_attribute.assert_any_call("mem0.event_type", "logfire_test")
        mock_span.set_attribute.assert_any_call("mem0.record_id", str(result["base_log_id"]))
        mock_span.set_attribute.assert_any_call("layer", "service")

    @patch("src.backend.cc.logging.logfire")
    async def test_logfire_graceful_degradation(self, mock_logfire: Mock, test_db_session: AsyncSession) -> None:
        """Test graceful degradation when Logfire operations fail."""
        mock_span = Mock()
        mock_span.set_attribute.side_effect = RuntimeError("Logfire error")  # Use RuntimeError which is caught
        mock_logfire.current_span.return_value = mock_span

        # Should not raise exception, but complete logging
        result = await log_l1(db=test_db_session, event_type="error_test", payload={"test": "data"})

        # Verify logging completed despite Logfire error
        assert "base_log_id" in result
        base_log = await test_db_session.get(BaseLog, result["base_log_id"])
        assert base_log is not None


class TestLogL1ParameterHandling:
    """Test parameter validation and edge cases."""

    async def test_empty_payload(self, test_db_session: AsyncSession) -> None:
        """Test handling of empty payload."""
        result = await log_l1(db=test_db_session, event_type="empty_test", payload={})

        # Should handle empty payload gracefully
        event_log = await test_db_session.get(EventLog, result["event_log_id"])
        assert event_log is not None
        assert event_log.event_data == {}

    async def test_partial_prompt_data(self, test_db_session: AsyncSession) -> None:
        """Test handling of partial prompt data."""
        partial_prompt_data = {"prompt_text": "Partial prompt only"}

        result = await log_l1(db=test_db_session, event_type="partial_test", prompt_data=partial_prompt_data)

        # Should handle partial data with defaults
        prompt_trace = await test_db_session.get(PromptTrace, result["prompt_trace_id"])
        assert prompt_trace is not None
        assert prompt_trace.prompt_text == "Partial prompt only"
        assert prompt_trace.response_text == ""  # Default from implementation
        assert prompt_trace.execution_time_ms == 0  # Default from implementation
        assert prompt_trace.token_count == 0  # Default from implementation

    async def test_complex_payload_data(self, test_db_session: AsyncSession) -> None:
        """Test handling of complex nested payload data."""
        complex_payload = {
            "user": {"id": 123, "name": "John"},
            "action": "complex_operation",
            "metadata": {
                "context": {"feature_flags": {"flag_a": True}},
                "metrics": {"duration_ms": 1500},
            },
        }

        result = await log_l1(db=test_db_session, event_type="complex_test", payload=complex_payload)

        # Verify complex data is stored correctly
        base_log = await test_db_session.get(BaseLog, result["base_log_id"])
        event_log = await test_db_session.get(EventLog, result["event_log_id"])

        assert base_log is not None
        assert event_log is not None
        assert base_log.payload == complex_payload
        assert event_log.event_data == complex_payload
        assert event_log.event_data is not None
        assert event_log.event_data["user"]["name"] == "John"
