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

# Constants for test values
MAX_TIME_DIFFERENCE_SECONDS = 0.001  # Less than 1ms difference
PERFORMANCE_TARGET_MICROSECONDS = 50.0  # Target performance budget
PERFORMANCE_ITERATIONS = 1000  # Number of test iterations
MICROSECONDS_MULTIPLIER = 1_000_000  # Conversion factor for microseconds
EXPECTED_SCHEMA_VERSION = 1


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

        # Verify envelope properties
        expected_log_id = envelope.base_log_id == base_log_id
        pytest.assume(expected_log_id)

        expected_source = envelope.source_module == "backend.cc.logging"
        pytest.assume(expected_source)

        expected_event_type = envelope.event_type == EventType.PROMPT_TRACE
        pytest.assume(expected_event_type)

        expected_data = envelope.data == {"test": "value"}
        pytest.assume(expected_data)

        expected_schema_version = envelope.schema_version == EXPECTED_SCHEMA_VERSION
        pytest.assume(expected_schema_version)

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

        # Verify required fields are reported as missing
        expected_subset = expected_fields.issubset(missing_fields)
        pytest.assume(expected_subset)

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

        # Verify event_type error is present
        expected_event_type_error = any(error["loc"] == ("event_type",) for error in errors)
        pytest.assume(expected_event_type_error)

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

        # Verify timestamp format
        expected_timestamp_format = json_data["timestamp"] == "2025-06-22T16:34:15.812000Z"
        pytest.assume(expected_timestamp_format)


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
        # Verify all required fields are present
        expected_fields_present = set(parsed.keys()) == required_fields
        pytest.assume(expected_fields_present)

        # Verify data types and values
        expected_log_id = uuid.UUID(parsed["base_log_id"]) == base_log_id
        pytest.assume(expected_log_id)

        expected_source_module = parsed["source_module"] == "backend.cc.logging"
        pytest.assume(expected_source_module)

        expected_event_type = parsed["event_type"] == "prompt_trace"
        pytest.assume(expected_event_type)

        expected_data = parsed["data"] == {"test": "value"}
        pytest.assume(expected_data)

        expected_schema_version = parsed["_schema_version"] == EXPECTED_SCHEMA_VERSION
        pytest.assume(expected_schema_version)

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
        expected_log_id = parsed_envelope.base_log_id == base_log_id
        pytest.assume(expected_log_id)

        expected_source_module = parsed_envelope.source_module == source_module
        pytest.assume(expected_source_module)

        expected_event_type = parsed_envelope.event_type == event_type
        pytest.assume(expected_event_type)

        expected_data = parsed_envelope.data == data
        pytest.assume(expected_data)

        # Timestamp comparison (handle potential microsecond precision differences)
        time_diff = abs((parsed_envelope.timestamp - timestamp).total_seconds())
        expected_time_precision = time_diff < MAX_TIME_DIFFERENCE_SECONDS
        pytest.assume(expected_time_precision)

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

        # Verify parsing from bytes
        expected_log_id = parsed_envelope.base_log_id == base_log_id
        pytest.assume(expected_log_id)

        expected_event_type = parsed_envelope.event_type == EventType.PROMPT_TRACE
        pytest.assume(expected_event_type)

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

        # Time iterations
        total_time = timeit.timeit(build_test_message, number=PERFORMANCE_ITERATIONS)
        avg_time_microseconds = (total_time / PERFORMANCE_ITERATIONS) * MICROSECONDS_MULTIPLIER

        # Should be ≤ target performance budget per call
        performance_msg = (
            f"Average time {avg_time_microseconds:.2f}µs exceeds " f"{PERFORMANCE_TARGET_MICROSECONDS}µs target"
        )
        expected_performance = avg_time_microseconds <= PERFORMANCE_TARGET_MICROSECONDS
        pytest.assume(expected_performance, performance_msg)


class TestEventType:
    """Test EventType enum validation and serialization."""

    def test_event_type_enum_values(self) -> None:
        """Test that EventType enum has correct values."""
        # Verify enum values
        expected_prompt_trace = EventType.PROMPT_TRACE.value == "prompt_trace"
        pytest.assume(expected_prompt_trace)

        expected_event_log = EventType.EVENT_LOG.value == "event_log"
        pytest.assume(expected_event_log)

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

        # Verify enum serialization
        expected_serialization = json_data["event_type"] == "prompt_trace"
        pytest.assume(expected_serialization)
