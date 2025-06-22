"""Tests for standardized message format utilities.

This module tests the MessageEnvelope Pydantic model and helper functions
for building and parsing standardized messages for Redis pub/sub communication.
"""

import json
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.common.message_format import EventType, MessageEnvelope, build_message, parse_message


class TestMessageEnvelope:
    """Test MessageEnvelope Pydantic model validation and serialization."""

    def test_valid_message_envelope_creation(self) -> None:
        """Test creating a valid MessageEnvelope with all required fields."""
        base_log_id = uuid.uuid4()
        test_data = {
            "base_log_id": base_log_id,
            "source_module": "backend.cc.logging",
            "timestamp": datetime.now(UTC),
            "trace_id": "otel-trace-123",
            "request_id": "req-456",
            "event_type": EventType.PROMPT_TRACE,
            "data": {"test": "value"},
        }

        envelope = MessageEnvelope(**test_data)

        assert envelope.base_log_id == base_log_id
        assert envelope.source_module == "backend.cc.logging"
        assert envelope.event_type == EventType.PROMPT_TRACE
        assert envelope.data == {"test": "value"}
        assert envelope.schema_version == 1

    def test_validation_missing_required_field_fails(self) -> None:
        """Test that missing required fields raise ValidationError."""
        incomplete_data = {
            "base_log_id": uuid.uuid4(),
            "source_module": "backend.cc.logging",
            # Missing timestamp, trace_id, request_id, event_type, data
        }

        with pytest.raises(ValidationError) as exc_info:
            MessageEnvelope(**incomplete_data)

        errors = exc_info.value.errors()
        missing_fields = {error["loc"][0] for error in errors}
        expected_fields = {"timestamp", "trace_id", "request_id", "event_type", "data"}
        assert expected_fields.issubset(missing_fields)

    def test_enum_validation_invalid_event_type(self) -> None:
        """Test that invalid event_type values are rejected."""
        test_data = {
            "base_log_id": uuid.uuid4(),
            "source_module": "backend.cc.logging",
            "timestamp": datetime.now(UTC),
            "trace_id": "otel-trace-123",
            "request_id": "req-456",
            "event_type": "INVALID_TYPE",  # Invalid enum value
            "data": {"test": "value"},
        }

        with pytest.raises(ValidationError) as exc_info:
            MessageEnvelope(**test_data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("event_type",) for error in errors)

    def test_timestamp_serialization_format(self) -> None:
        """Test that timestamp is serialized to RFC3339 format with Z suffix."""
        test_time = datetime(2025, 6, 22, 16, 34, 15, 812000, UTC)
        envelope = MessageEnvelope(
            base_log_id=uuid.uuid4(),
            source_module="backend.cc.logging",
            timestamp=test_time,
            trace_id="otel-trace-123",
            request_id="req-456",
            event_type=EventType.EVENT_LOG,
            data={"test": "value"},
        )

        json_data = json.loads(envelope.model_dump_json())
        assert json_data["timestamp"] == "2025-06-22T16:34:15.812000Z"


class TestHelperFunctions:
    """Test build_message and parse_message helper functions."""

    def test_build_message_has_required_fields(self) -> None:
        """Test that build_message generates JSON with all required fields."""
        base_log_id = uuid.uuid4()
        json_str = build_message(
            base_log_id=base_log_id,
            source_module="backend.cc.logging",
            timestamp=datetime.now(UTC),
            trace_id="otel-trace-123",
            request_id="req-456",
            event_type=EventType.PROMPT_TRACE,
            data={"test": "value"},
        )

        # Verify it's valid JSON
        parsed = json.loads(json_str)

        # Check all required fields are present (using alias names)
        required_fields = {
            "base_log_id",
            "source_module",
            "timestamp",
            "trace_id",
            "request_id",
            "event_type",
            "data",
            "_schema_version",
        }
        assert set(parsed.keys()) == required_fields

        # Verify data types and values
        assert uuid.UUID(parsed["base_log_id"]) == base_log_id
        assert parsed["source_module"] == "backend.cc.logging"
        assert parsed["event_type"] == "prompt_trace"
        assert parsed["data"] == {"test": "value"}
        assert parsed["_schema_version"] == 1

    def test_round_trip_serialization(self) -> None:
        """Test that build_message -> parse_message preserves data."""
        base_log_id = uuid.uuid4()
        source_module = "backend.cc.logging"
        timestamp = datetime.now(UTC)
        trace_id = "otel-trace-123"
        request_id = "req-456"
        event_type = EventType.EVENT_LOG
        data = {"complex": {"nested": "data", "numbers": [1, 2, 3]}}

        # Build message
        json_str = build_message(
            base_log_id=base_log_id,
            source_module=source_module,
            timestamp=timestamp,
            trace_id=trace_id,
            request_id=request_id,
            event_type=event_type,
            data=data,
        )

        # Parse message
        parsed_envelope = parse_message(json_str)

        # Verify round-trip preservation
        assert parsed_envelope.base_log_id == base_log_id
        assert parsed_envelope.source_module == source_module
        assert parsed_envelope.event_type == event_type
        assert parsed_envelope.data == data

        # Timestamp comparison (handle potential microsecond precision differences)
        time_diff = abs((parsed_envelope.timestamp - timestamp).total_seconds())
        assert time_diff < 0.001  # Less than 1ms difference

    def test_parse_message_bytes_input(self) -> None:
        """Test that parse_message can handle bytes input from Redis."""
        base_log_id = uuid.uuid4()
        json_str = build_message(
            base_log_id=base_log_id,
            source_module="backend.cc.logging",
            timestamp=datetime.now(UTC),
            trace_id="otel-trace-123",
            request_id="req-456",
            event_type=EventType.PROMPT_TRACE,
            data={"test": "value"},
        )

        # Convert to bytes (as Redis would provide)
        json_bytes = json_str.encode("utf-8")

        # Parse from bytes
        parsed_envelope = parse_message(json_bytes)

        assert parsed_envelope.base_log_id == base_log_id
        assert parsed_envelope.event_type == EventType.PROMPT_TRACE

    def test_performance_budget(self) -> None:
        """Test that build_message meets performance target of ≤ 50µs."""
        import timeit

        base_log_id = uuid.uuid4()

        def build_test_message() -> str:
            return build_message(
                base_log_id=base_log_id,
                source_module="backend.cc.logging",
                timestamp=datetime.now(UTC),
                trace_id="otel-trace-123",
                request_id="req-456",
                event_type=EventType.EVENT_LOG,
                data={"test": "value"},
            )

        # Time 1000 executions
        total_time = timeit.timeit(build_test_message, number=1000)
        avg_time_microseconds = (total_time / 1000) * 1_000_000

        # Should be ≤ 50µs per call
        assert avg_time_microseconds <= 50.0, f"Average time {avg_time_microseconds:.2f}µs exceeds 50µs target"


class TestEventType:
    """Test EventType enum validation and serialization."""

    def test_event_type_enum_values(self) -> None:
        """Test that EventType enum has correct values."""
        assert EventType.PROMPT_TRACE.value == "prompt_trace"
        assert EventType.EVENT_LOG.value == "event_log"

    def test_event_type_enum_serialization(self) -> None:
        """Test that EventType enum serializes correctly in JSON."""
        envelope = MessageEnvelope(
            base_log_id=uuid.uuid4(),
            source_module="backend.cc.logging",
            timestamp=datetime.now(UTC),
            trace_id="otel-trace-123",
            request_id="req-456",
            event_type=EventType.PROMPT_TRACE,
            data={"test": "value"},
        )

        json_data = json.loads(envelope.model_dump_json())
        assert json_data["event_type"] == "prompt_trace"
