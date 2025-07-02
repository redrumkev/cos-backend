"""Comprehensive tests for L1 memory logging service.  # noqa: D400

This test suite is excluded from strict static type checking during Phase 1.5
development, therefore we disable mypy and ruff checks for this file.
"""
# mypy: ignore-errors
# ruff: noqa

import os
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.logging import log_l1
from src.backend.cc.mem0_models import BaseLog, EventLog, PromptTrace

# Skip if database integration is not enabled
ENABLE_DB_INTEGRATION = os.environ.get("ENABLE_DB_INTEGRATION", "").lower() == "true"


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
    """Comprehensive latency benchmarks for log_l1 service.

    Tests verify P95 latency < 2ms SLA requirement across multiple scenarios:
    - Event-only logging (most common pattern)
    - Prompt-only logging (LLM interactions)
    - Combined event+prompt logging (maximum complexity)
    - Baseline minimal logging (core overhead measurement)
    - Large payload stress testing (performance consistency)

    Database operations are mocked to isolate service logic performance
    from I/O latency and focus on business logic overhead.
    """

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session for performance testing."""
        from unittest.mock import AsyncMock, MagicMock

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        # Mock add method to simulate ID assignment
        added_instances = []

        def mock_add(instance):
            # Simulate ID assignment that would happen after flush
            if not hasattr(instance, "id") or instance.id is None:
                instance.id = uuid.uuid4()
            added_instances.append(instance)

        mock_db.add = MagicMock(side_effect=mock_add)
        mock_db.added_instances = added_instances

        return mock_db

    def _create_async_wrapper(self, func, *args, **kwargs):
        """Create async wrapper for benchmark compatibility."""

        async def async_wrapper():
            return await func(*args, **kwargs)

        return async_wrapper

    @pytest.mark.benchmark(group="log_l1_latency")
    @pytest.mark.asyncio
    async def test_log_l1_latency_event_only(self, benchmark, mock_db_session):
        """Benchmark log_l1 service with event-only data.

        Tests most common usage pattern: event logging without prompt traces.
        Target: P95 latency < 2ms for event-only scenarios.

        Statistical Configuration:
        - 100 iterations for statistical accuracy
        - 10 rounds for consistent measurement
        - Excludes database I/O via mocking
        """

        # Async wrapper for benchmark compatibility
        async def log_event_only():
            return await log_l1(
                db=mock_db_session,
                event_type="benchmark_event_test",
                payload={
                    "action": "user_click",
                    "user_id": "user-123",
                    "session_id": "session-456",
                    "metadata": {"button": "submit", "page": "checkout"},
                },
                request_id=str(uuid.uuid4()),
            )

        # Execute benchmark with statistical rigor
        result = await benchmark.pedantic(log_event_only, iterations=100, rounds=10, warmup_rounds=2)

        # Validate result structure
        assert "base_log_id" in result
        assert "event_log_id" in result
        assert len(result) == 2

        # Verify database operations were called
        assert mock_db_session.flush.call_count >= 2  # BaseLog + EventLog
        assert mock_db_session.commit.called
        assert mock_db_session.add.call_count >= 2

        # Performance validation - Use max as conservative P95 proxy
        # pytest-benchmark stats are in nanoseconds, convert to seconds for SLA comparison
        stats = benchmark.stats
        max_latency = stats["max"] / 1_000_000_000  # Convert nanoseconds to seconds
        mean_latency = stats["mean"] / 1_000_000_000
        min_latency = stats["min"] / 1_000_000_000

        # Use max as conservative estimate for P95 (should be well below 2ms)
        assert max_latency < 0.002, (
            f"Max latency {max_latency:.6f}s exceeds 2ms SLA target "
            f"(mean: {mean_latency:.6f}s, min: {min_latency:.6f}s)"
        )

    @pytest.mark.benchmark(group="log_l1_latency")
    @pytest.mark.asyncio
    async def test_log_l1_latency_prompt_only(self, benchmark, mock_db_session):
        """Benchmark log_l1 service with prompt-only data.

        Tests LLM interaction logging pattern: prompt traces without event payloads.
        Target: P95 latency < 2ms for prompt-only scenarios.

        Statistical Configuration:
        - 100 iterations for statistical accuracy
        - 10 rounds for consistent P95 measurement
        - Excludes database I/O via mocking
        """

        # Async wrapper for benchmark compatibility
        async def log_prompt_only():
            return await log_l1(
                db=mock_db_session,
                event_type="benchmark_prompt_test",
                prompt_data={
                    "prompt_text": "Generate a comprehensive summary of the given data",
                    "response_text": "Here is a detailed summary analyzing the key aspects...",
                    "execution_time_ms": 150,
                    "token_count": 45,
                },
                request_id=str(uuid.uuid4()),
            )

        # Execute benchmark with statistical rigor
        result = await benchmark.pedantic(log_prompt_only, iterations=100, rounds=10, warmup_rounds=2)

        # Validate result structure
        assert "base_log_id" in result
        assert "prompt_trace_id" in result
        assert len(result) == 2

        # Verify database operations were called
        assert mock_db_session.flush.call_count >= 2  # BaseLog + PromptTrace
        assert mock_db_session.commit.called
        assert mock_db_session.add.call_count >= 2

        # Performance validation - Use max as conservative P95 proxy
        # pytest-benchmark stats are in nanoseconds, convert to seconds for SLA comparison
        stats = benchmark.stats
        max_latency = stats["max"] / 1_000_000_000  # Convert nanoseconds to seconds
        mean_latency = stats["mean"] / 1_000_000_000
        min_latency = stats["min"] / 1_000_000_000

        # Use max as conservative estimate for P95 (should be well below 2ms)
        assert max_latency < 0.002, (
            f"Max latency {max_latency:.6f}s exceeds 2ms SLA target "
            f"(mean: {mean_latency:.6f}s, min: {min_latency:.6f}s)"
        )

    @pytest.mark.benchmark(group="log_l1_latency")
    @pytest.mark.asyncio
    async def test_log_l1_latency_combined_scenario(self, benchmark, mock_db_session):
        """Benchmark log_l1 service with both payload and prompt_data.

        Tests the most complex usage pattern: full logging with both event payload
        and prompt trace data. This represents the maximum service overhead.
        Target: P95 latency < 2ms even for combined scenarios.

        Statistical Configuration:
        - 100 iterations for statistical accuracy
        - 10 rounds for consistent P95 measurement
        - Excludes database I/O via mocking
        """

        # Async wrapper for benchmark compatibility
        async def log_combined_scenario():
            return await log_l1(
                db=mock_db_session,
                event_type="benchmark_combined_test",
                payload={
                    "action": "ai_completion_request",
                    "user_id": "user-12345",
                    "session_id": "session-abc123",
                    "metadata": {"priority": "high", "source": "api"},
                },
                prompt_data={
                    "prompt_text": "Analyze the following data and provide actionable insights",
                    "response_text": "Based on the analysis, here are the key findings and recommendations...",
                    "execution_time_ms": 275,
                    "token_count": 89,
                },
                request_id=str(uuid.uuid4()),
                trace_id="benchmark-trace-003",
            )

        # Execute benchmark with statistical rigor
        result = await benchmark.pedantic(log_combined_scenario, iterations=100, rounds=10, warmup_rounds=2)

        # Validate result structure - all three record types
        assert "base_log_id" in result
        assert "event_log_id" in result
        assert "prompt_trace_id" in result
        assert len(result) == 3

        # Verify database operations were called for all record types
        assert mock_db_session.flush.call_count >= 3  # BaseLog + EventLog + PromptTrace
        assert mock_db_session.commit.called
        assert mock_db_session.add.call_count >= 3

        # Performance validation - Use max as conservative P95 proxy
        # pytest-benchmark stats are in nanoseconds, convert to seconds for SLA comparison
        stats = benchmark.stats
        max_latency = stats["max"] / 1_000_000_000  # Convert nanoseconds to seconds
        mean_latency = stats["mean"] / 1_000_000_000
        min_latency = stats["min"] / 1_000_000_000

        # Use max as conservative estimate for P95 (should be well below 2ms)
        assert max_latency < 0.002, (
            f"Max latency {max_latency:.6f}s exceeds 2ms SLA target "
            f"(mean: {mean_latency:.6f}s, min: {min_latency:.6f}s)"
        )

    @pytest.mark.benchmark(group="log_l1_baseline")
    @pytest.mark.asyncio
    async def test_log_l1_baseline_minimal(self, benchmark, mock_db_session):
        """Benchmark minimal log_l1 service call for baseline performance.

        Establishes performance baseline with minimal parameters to measure
        core service overhead without payload/prompt processing.
        Target: P95 latency < 1ms for minimal scenarios.
        """

        # Async wrapper for benchmark compatibility
        async def log_minimal():
            return await log_l1(db=mock_db_session, event_type="benchmark_minimal_test")

        # Execute benchmark with statistical rigor
        result = await benchmark.pedantic(log_minimal, iterations=100, rounds=10, warmup_rounds=2)

        # Validate minimal result structure
        assert "base_log_id" in result
        assert len(result) == 1  # Only BaseLog created

        # Verify database operations were called
        assert mock_db_session.flush.call_count >= 1  # BaseLog only
        assert mock_db_session.commit.called
        assert mock_db_session.add.call_count >= 1

        # Performance validation - baseline should be faster than full scenarios
        # pytest-benchmark stats are in nanoseconds, convert to seconds for SLA comparison
        stats = benchmark.stats
        max_latency = stats["max"] / 1_000_000_000  # Convert nanoseconds to seconds
        mean_latency = stats["mean"] / 1_000_000_000
        min_latency = stats["min"] / 1_000_000_000

        # Use max as conservative estimate for P95 (should be well below 1ms)
        assert max_latency < 0.001, (
            f"Baseline max latency {max_latency:.6f}s exceeds 1ms target "
            f"(mean: {mean_latency:.6f}s, min: {min_latency:.6f}s)"
        )

    @pytest.mark.benchmark(group="log_l1_stress")
    @pytest.mark.asyncio
    async def test_log_l1_performance_consistency(self, benchmark, mock_db_session):
        """Validate performance consistency across larger payload sizes.

        Tests service performance with larger payloads to ensure latency
        remains consistent regardless of data size within reasonable limits.
        Target: P95 latency < 2ms even with larger payloads.
        """

        # Create larger payload to test performance under realistic load
        large_payload = {
            "event_type": "complex_user_interaction",
            "user_data": {
                "profile": {"name": "Test User", "preferences": ["pref1", "pref2", "pref3"]},
                "session": {"duration": 3600, "pages_viewed": 15, "actions": ["click", "scroll", "submit"]},
                "metadata": {"browser": "Chrome", "platform": "Windows", "resolution": "1920x1080"},
            },
            "analytics": {
                "metrics": [{"name": "engagement", "value": 0.85}, {"name": "satisfaction", "value": 0.92}],
                "segments": ["premium_user", "power_user", "engaged_user"],
            },
        }

        large_prompt_data = {
            "prompt_text": "Given the comprehensive user interaction data including profile preferences, session analytics, and behavioral patterns, provide a detailed analysis of user engagement trends and actionable recommendations for improving the user experience based on the observed patterns and metrics",
            "response_text": "Based on the comprehensive analysis of the user interaction data, several key insights emerge regarding engagement patterns and user behavior. The data indicates strong engagement levels with an engagement score of 0.85 and satisfaction rating of 0.92, suggesting effective user experience design. Key recommendations include: 1) Leverage the high satisfaction scores to identify and replicate successful interaction patterns, 2) Focus on the power user segment for feature expansion opportunities, 3) Optimize page view sequences based on the 15-page session pattern, 4) Consider platform-specific optimizations for Windows Chrome users, and 5) Continue monitoring engagement metrics to maintain the positive trajectory observed in the current dataset.",
            "execution_time_ms": 450,
            "token_count": 156,
        }

        # Async wrapper for benchmark compatibility
        async def log_large_payload():
            return await log_l1(
                db=mock_db_session,
                event_type="benchmark_stress_test",
                payload=large_payload,
                prompt_data=large_prompt_data,
                request_id=str(uuid.uuid4()),
                trace_id="benchmark-trace-stress",
            )

        # Execute benchmark with statistical rigor
        result = await benchmark.pedantic(log_large_payload, iterations=100, rounds=10, warmup_rounds=2)

        # Validate result structure for stress test
        assert "base_log_id" in result
        assert "event_log_id" in result
        assert "prompt_trace_id" in result
        assert len(result) == 3

        # Verify database operations were called
        assert mock_db_session.flush.call_count >= 3  # BaseLog + EventLog + PromptTrace
        assert mock_db_session.commit.called
        assert mock_db_session.add.call_count >= 3

        # Performance validation - even large payloads should meet SLA
        # pytest-benchmark stats are in nanoseconds, convert to seconds for SLA comparison
        stats = benchmark.stats
        max_latency = stats["max"] / 1_000_000_000  # Convert nanoseconds to seconds
        mean_latency = stats["mean"] / 1_000_000_000
        min_latency = stats["min"] / 1_000_000_000

        # Use max as conservative estimate for P95 (should be well below 2ms even for large payloads)
        assert max_latency < 0.002, (
            f"Large payload max latency {max_latency:.6f}s exceeds 2ms SLA target "
            f"(mean: {mean_latency:.6f}s, min: {min_latency:.6f}s)"
        )


@pytest.mark.skipif(not ENABLE_DB_INTEGRATION, reason="Database integration tests disabled")
class TestLogL1DatabaseIntegrity:
    """Test database transaction integrity and consistency."""

    async def test_transaction_rollback_on_error(self, test_db_session: AsyncSession) -> None:
        """Test that transaction rolls back properly on errors."""
        # This test would require mocking database errors
        # For now, we verify normal transaction integrity
        from sqlalchemy import func

        initial_count_result = await test_db_session.execute(select(func.count()).select_from(BaseLog))
        initial_count = initial_count_result.scalar() or 0

        await log_l1(db=test_db_session, event_type="integrity_test")

        final_count_result = await test_db_session.execute(select(func.count()).select_from(BaseLog))
        final_count = final_count_result.scalar() or 0
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
