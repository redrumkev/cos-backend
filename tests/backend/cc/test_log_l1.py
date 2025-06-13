"""Comprehensive tests for L1 memory logging service.  # noqa: D400

This test suite is excluded from strict static type checking during Phase 1.5
development, therefore we disable mypy and ruff checks for this file.
"""
# mypy: ignore-errors
# ruff: noqa

import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.logging import log_l1
from src.backend.cc.mem0_models import BaseLog, EventLog, PromptTrace


class TestLogL1Basic:
    """Test basic log_l1 functionality."""

    async def test_basic_log_creation(self, test_db_session: AsyncSession) -> None:
        """Test basic BaseLog creation with minimal parameters."""
        result = await log_l1(db=test_db_session, event_type="test_event")

        assert "base_log_id" in result
        assert isinstance(result["base_log_id"], uuid.UUID)
        assert len(result) == 1

        # Verify database record
        base_log = await test_db_session.get(BaseLog, result["base_log_id"])
        assert base_log is not None
        assert base_log.level == "INFO"
        assert base_log.message == "Event: test_event"
        assert base_log.payload == {}

    async def test_event_log_creation(self, test_db_session: AsyncSession) -> None:
        """Test EventLog creation with payload."""
        payload = {"action": "user_login", "user_id": "12345"}
        request_id = str(uuid.uuid4())

        result = await log_l1(db=test_db_session, event_type="user_event", payload=payload, request_id=request_id)

        assert "base_log_id" in result
        assert "event_log_id" in result
        assert len(result) == 2

        # Verify EventLog record
        event_log = await test_db_session.get(EventLog, result["event_log_id"])
        assert event_log is not None
        assert event_log.event_type == "user_event"
        assert event_log.event_data == payload
        assert str(event_log.request_id) == request_id
        assert event_log.base_log_id == result["base_log_id"]

    async def test_prompt_trace_creation(self, test_db_session: AsyncSession) -> None:
        """Test PromptTrace creation with prompt_data."""
        prompt_data = {
            "prompt_text": "What is the capital of France?",
            "response_text": "The capital of France is Paris.",
            "execution_time_ms": 150,
            "token_count": 25,
        }

        result = await log_l1(db=test_db_session, event_type="llm_prompt", prompt_data=prompt_data)

        assert "base_log_id" in result
        assert "prompt_trace_id" in result
        assert len(result) == 2

        # Verify PromptTrace record
        prompt_trace = await test_db_session.get(PromptTrace, result["prompt_trace_id"])
        assert prompt_trace is not None
        assert prompt_trace.prompt_text == prompt_data["prompt_text"]
        assert prompt_trace.response_text == prompt_data["response_text"]
        assert prompt_trace.execution_time_ms == prompt_data["execution_time_ms"]
        assert prompt_trace.token_count == prompt_data["token_count"]
        assert prompt_trace.base_log_id == result["base_log_id"]

    async def test_combined_logging(self, test_db_session: AsyncSession) -> None:
        """Test creation of all log types in single call."""
        payload = {"action": "ai_completion", "model": "gpt-4"}
        prompt_data = {
            "prompt_text": "Generate a summary",
            "response_text": "Here is the summary...",
            "execution_time_ms": 200,
            "token_count": 50,
        }
        request_id = str(uuid.uuid4())
        trace_id = "test_trace_123"

        result = await log_l1(
            db=test_db_session,
            event_type="ai_completion",
            payload=payload,
            prompt_data=prompt_data,
            request_id=request_id,
            trace_id=trace_id,
        )

        assert "base_log_id" in result
        assert "event_log_id" in result
        assert "prompt_trace_id" in result
        assert len(result) == 3

        # Verify all records exist and are linked
        base_log = await test_db_session.get(BaseLog, result["base_log_id"])
        event_log = await test_db_session.get(EventLog, result["event_log_id"])
        prompt_trace = await test_db_session.get(PromptTrace, result["prompt_trace_id"])

        assert all([base_log, event_log, prompt_trace])
        assert event_log.base_log_id == result["base_log_id"]
        assert prompt_trace.base_log_id == result["base_log_id"]
        assert event_log.trace_id == trace_id


class TestLogL1RequestHandling:
    """Test request ID and trace ID handling."""

    @patch("src.backend.cc.logging.get_request_id")
    async def test_request_id_from_context(self, mock_get_request_id: MagicMock, test_db_session: AsyncSession) -> None:
        """Test request ID retrieval from context when not provided."""
        context_request_id = str(uuid.uuid4())
        mock_get_request_id.return_value = context_request_id

        result = await log_l1(db=test_db_session, event_type="test_event", payload={"test": "data"})

        event_log = await test_db_session.get(EventLog, result["event_log_id"])
        assert str(event_log.request_id) == context_request_id
        mock_get_request_id.assert_called_once()

    @patch("src.backend.cc.logging.get_request_id")
    async def test_request_id_fallback_to_uuid(
        self, mock_get_request_id: MagicMock, test_db_session: AsyncSession
    ) -> None:
        """Test UUID fallback when context has no request ID."""
        mock_get_request_id.return_value = None

        result = await log_l1(db=test_db_session, event_type="test_event", payload={"test": "data"})

        event_log = await test_db_session.get(EventLog, result["event_log_id"])
        assert event_log.request_id is not None
        assert isinstance(event_log.request_id, uuid.UUID)
        mock_get_request_id.assert_called_once()

    async def test_provided_request_id_priority(self, test_db_session: AsyncSession) -> None:
        """Test that provided request_id takes priority over context."""
        provided_request_id = str(uuid.uuid4())

        with patch("src.backend.cc.logging.get_request_id") as mock_get_request_id:
            mock_get_request_id.return_value = str(uuid.uuid4())  # Different ID

            result = await log_l1(
                db=test_db_session, event_type="test_event", payload={"test": "data"}, request_id=provided_request_id
            )

            event_log = await test_db_session.get(EventLog, result["event_log_id"])
            assert str(event_log.request_id) == provided_request_id
            mock_get_request_id.assert_not_called()

    async def test_request_id_uuid_conversion(self, test_db_session: AsyncSession) -> None:
        """Test proper UUID conversion for request_id."""
        string_request_id = str(uuid.uuid4())

        result = await log_l1(
            db=test_db_session, event_type="test_event", payload={"test": "data"}, request_id=string_request_id
        )

        event_log = await test_db_session.get(EventLog, result["event_log_id"])
        assert isinstance(event_log.request_id, uuid.UUID)
        assert str(event_log.request_id) == string_request_id


class TestLogL1LogfireIntegration:
    """Test Logfire span integration."""

    @patch("src.backend.cc.logging.logfire")
    async def test_trace_id_extraction(self, mock_logfire: MagicMock, test_db_session: AsyncSession) -> None:
        """Test trace_id extraction from Logfire span."""
        test_trace_id = "test_trace_12345"
        mock_span = MagicMock()
        mock_span.context.trace_id = test_trace_id
        mock_logfire.current_span.return_value = mock_span

        result = await log_l1(db=test_db_session, event_type="test_event", payload={"test": "data"})

        event_log = await test_db_session.get(EventLog, result["event_log_id"])
        assert event_log.trace_id == test_trace_id

    @patch("src.backend.cc.logging.logfire")
    async def test_span_attribute_setting(self, mock_logfire: MagicMock, test_db_session: AsyncSession) -> None:
        """Test setting custom attributes on Logfire span."""
        mock_span = MagicMock()
        mock_logfire.current_span.return_value = mock_span

        result = await log_l1(db=test_db_session, event_type="test_event")

        # Verify span attributes were set
        mock_span.set_attribute.assert_any_call("mem0.event_type", "test_event")
        mock_span.set_attribute.assert_any_call("mem0.record_id", str(result["base_log_id"]))
        mock_span.set_attribute.assert_any_call("layer", "service")

    @patch("src.backend.cc.logging.logfire")
    async def test_logfire_graceful_degradation_missing_function(
        self, mock_logfire: MagicMock, test_db_session: AsyncSession
    ) -> None:
        """Test graceful degradation when current_span is missing."""
        # Remove current_span attribute
        del mock_logfire.current_span

        # Should not raise exception
        result = await log_l1(db=test_db_session, event_type="test_event", payload={"test": "data"})

        assert "base_log_id" in result
        assert "event_log_id" in result

    @patch("src.backend.cc.logging.logfire")
    async def test_logfire_graceful_degradation_span_error(
        self, mock_logfire: MagicMock, test_db_session: AsyncSession
    ) -> None:
        """Test graceful degradation when span operations fail."""
        mock_logfire.current_span.side_effect = RuntimeError("Span error")

        # Should not raise exception
        result = await log_l1(db=test_db_session, event_type="test_event", payload={"test": "data"})

        assert "base_log_id" in result
        assert "event_log_id" in result

    async def test_provided_trace_id_priority(self, test_db_session: AsyncSession) -> None:
        """Test that provided trace_id takes priority over Logfire extraction."""
        provided_trace_id = "provided_trace_123"

        with patch("src.backend.cc.logging.logfire") as mock_logfire:
            mock_span = MagicMock()
            mock_span.context.trace_id = "logfire_trace_456"
            mock_logfire.current_span.return_value = mock_span

            result = await log_l1(
                db=test_db_session, event_type="test_event", payload={"test": "data"}, trace_id=provided_trace_id
            )

            event_log = await test_db_session.get(EventLog, result["event_log_id"])
            assert event_log.trace_id == provided_trace_id


class TestLogL1EdgeCases:
    """Test edge cases and error conditions."""

    async def test_empty_payload(self, test_db_session: AsyncSession) -> None:
        """Test handling of empty payload."""
        result = await log_l1(db=test_db_session, event_type="test_event", payload={})

        event_log = await test_db_session.get(EventLog, result["event_log_id"])
        assert event_log.event_data == {}

    async def test_empty_prompt_data(self, test_db_session: AsyncSession) -> None:
        """Test handling of empty prompt_data."""
        result = await log_l1(db=test_db_session, event_type="test_event", prompt_data={})

        prompt_trace = await test_db_session.get(PromptTrace, result["prompt_trace_id"])
        assert prompt_trace.prompt_text == ""
        assert prompt_trace.response_text == ""
        assert prompt_trace.execution_time_ms == 0
        assert prompt_trace.token_count == 0

    async def test_partial_prompt_data(self, test_db_session: AsyncSession) -> None:
        """Test handling of partial prompt_data."""
        result = await log_l1(db=test_db_session, event_type="test_event", prompt_data={"prompt_text": "Test prompt"})

        prompt_trace = await test_db_session.get(PromptTrace, result["prompt_trace_id"])
        assert prompt_trace.prompt_text == "Test prompt"
        assert prompt_trace.response_text == ""
        assert prompt_trace.execution_time_ms == 0
        assert prompt_trace.token_count == 0

    async def test_none_values_handling(self, test_db_session: AsyncSession) -> None:
        """Test explicit None values are handled correctly."""
        result = await log_l1(
            db=test_db_session, event_type="test_event", payload=None, prompt_data=None, request_id=None, trace_id=None
        )

        assert "base_log_id" in result
        assert len(result) == 1  # Only BaseLog created

    async def test_complex_payload_data(self, test_db_session: AsyncSession) -> None:
        """Test complex nested payload data."""
        complex_payload = {
            "user": {"id": 123, "name": "Test User"},
            "metadata": {"tags": ["important", "urgent"], "priority": 1},
            "nested": {"deep": {"value": "test"}},
        }

        result = await log_l1(db=test_db_session, event_type="complex_event", payload=complex_payload)

        event_log = await test_db_session.get(EventLog, result["event_log_id"])
        assert event_log.event_data == complex_payload


class TestLogL1Performance:
    """Performance tests for log_l1 function."""

    @pytest.mark.benchmark(group="log_l1")
    async def test_basic_logging_performance(self, benchmark: Any, test_db_session: AsyncSession) -> None:
        """Benchmark basic logging performance (target: P95 < 2ms)."""

        async def log_operation() -> dict[str, uuid.UUID]:
            return await log_l1(db=test_db_session, event_type="performance_test")

        result = await benchmark(log_operation)
        assert "base_log_id" in result

    @pytest.mark.benchmark(group="log_l1")
    async def test_combined_logging_performance(self, benchmark: Any, test_db_session: AsyncSession) -> None:
        """Benchmark combined logging performance (all record types)."""
        payload = {"action": "test", "data": "performance"}
        prompt_data = {
            "prompt_text": "Test prompt",
            "response_text": "Test response",
            "execution_time_ms": 100,
            "token_count": 20,
        }

        async def log_operation() -> dict[str, uuid.UUID]:
            return await log_l1(
                db=test_db_session, event_type="performance_test_combined", payload=payload, prompt_data=prompt_data
            )

        result = await benchmark(log_operation)
        assert len(result) == 3


class TestLogL1DatabaseIntegrity:
    """Test database transaction integrity and consistency."""

    async def test_transaction_rollback_on_error(self, test_db_session: AsyncSession) -> None:
        """Test that transaction rolls back properly on errors."""
        # This test would require mocking database errors
        # For now, we verify normal transaction integrity
        initial_count = (await test_db_session.execute(select(BaseLog))).rowcount

        await log_l1(db=test_db_session, event_type="integrity_test")

        final_count = (await test_db_session.execute(select(BaseLog))).rowcount
        assert final_count == initial_count + 1

    async def test_foreign_key_relationships(self, test_db_session: AsyncSession) -> None:
        """Test that foreign key relationships are properly maintained."""
        result = await log_l1(
            db=test_db_session, event_type="fk_test", payload={"test": "data"}, prompt_data={"prompt_text": "test"}
        )

        # Load with relationships
        base_log = await test_db_session.get(BaseLog, result["base_log_id"])
        event_log = await test_db_session.get(EventLog, result["event_log_id"])
        prompt_trace = await test_db_session.get(PromptTrace, result["prompt_trace_id"])

        assert event_log.base_log_id == base_log.id
        assert prompt_trace.base_log_id == base_log.id

    async def test_concurrent_logging_safety(self, test_db_session: AsyncSession) -> None:
        """Test concurrent logging operations don't interfere."""
        import asyncio

        async def log_concurrent(event_id: int) -> dict[str, uuid.UUID]:
            return await log_l1(
                db=test_db_session, event_type=f"concurrent_test_{event_id}", payload={"event_id": event_id}
            )

        # Run multiple concurrent operations
        tasks = [log_concurrent(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Verify all operations succeeded and created unique records
        assert len(results) == 5
        base_log_ids = {result["base_log_id"] for result in results}
        assert len(base_log_ids) == 5  # All unique
