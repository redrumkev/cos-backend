"""Tests for standardized message format utilities.

This module tests the MessageEnvelope Pydantic model and helper functions
for building and parsing standardized messages for Redis pub/sub communication.
"""

import json
import subprocess
import sys
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
        assert envelope.base_log_id == base_log_id
        assert envelope.source_module == "backend.cc.logging"
        assert envelope.event_type == EventType.PROMPT_TRACE
        assert envelope.data == {"test": "value"}
        assert envelope.schema_version == EXPECTED_SCHEMA_VERSION

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

        # Verify event_type error is present
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

        # Verify timestamp format
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
        # Verify all required fields are present
        assert set(parsed.keys()) == required_fields

        # Verify data types and values
        assert uuid.UUID(parsed["base_log_id"]) == base_log_id
        assert parsed["source_module"] == "backend.cc.logging"
        assert parsed["event_type"] == "prompt_trace"
        assert parsed["data"] == {"test": "value"}
        assert parsed["_schema_version"] == EXPECTED_SCHEMA_VERSION

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
        assert time_diff < MAX_TIME_DIFFERENCE_SECONDS

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

        # Time iterations
        total_time = timeit.timeit(build_test_message, number=PERFORMANCE_ITERATIONS)
        avg_time_microseconds = (total_time / PERFORMANCE_ITERATIONS) * MICROSECONDS_MULTIPLIER

        # Should be ≤ target performance budget per call
        performance_msg = (
            f"Average time {avg_time_microseconds:.2f}µs exceeds {PERFORMANCE_TARGET_MICROSECONDS}µs target"
        )
        assert avg_time_microseconds <= PERFORMANCE_TARGET_MICROSECONDS, performance_msg


class TestEventType:
    """Test EventType enum validation and serialization."""

    def test_event_type_enum_values(self) -> None:
        """Test that EventType enum has correct values."""
        # Verify enum values
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

        # Verify enum serialization
        assert json_data["event_type"] == "prompt_trace"


class TestOrjsonImportFallback:
    """Test orjson import fallback behavior."""

    def test_message_format_without_orjson(self) -> None:
        """Test that message_format works without orjson installed."""
        # Create a test script that imports message_format without orjson
        test_script = """
import sys
import json

# Clear any existing imports
for module in list(sys.modules.keys()):
    if module.startswith('src.common.message_format') or module == 'orjson':
        del sys.modules[module]

# Add a custom import hook to make orjson import fail
class OrjsonBlocker:
    def find_spec(self, fullname, path, target=None):
        if fullname == 'orjson':
            # Return a spec that will fail on load
            import importlib.machinery
            spec = importlib.machinery.ModuleSpec(fullname, None)
            spec.loader = self
            return spec
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        raise ImportError("orjson blocked for testing")

# Insert the blocker at the beginning
sys.meta_path.insert(0, OrjsonBlocker())

# Now import message_format - should hit the ImportError branch
from src.common.message_format import HAS_ORJSON, build_message, EventType
import uuid
from datetime import datetime, UTC

# Verify orjson is not available
assert not HAS_ORJSON, f"HAS_ORJSON should be False when orjson import fails, but got {HAS_ORJSON}"

# Test that functionality still works without orjson
msg = build_message(
    base_log_id=uuid.uuid4(),
    source_module="test",
    timestamp=datetime.now(UTC),
    trace_id="test-123",
    request_id="req-456",
    event_type=EventType.EVENT_LOG,
    data={"test": "value"}
)

# Verify message was created successfully
assert isinstance(msg, str)
assert len(msg) > 0
parsed = json.loads(msg)
assert parsed["source_module"] == "test"
assert parsed["event_type"] == "event_log"

print("SUCCESS: message_format works without orjson")
"""

        # Run the test script in a subprocess with a clean environment
        import os

        env = os.environ.copy()
        # Ensure Python path is set correctly
        env["PYTHONPATH"] = "/Users/kevinmba/dev/cos"

        result = subprocess.run(
            [sys.executable, "-c", test_script], capture_output=True, text=True, cwd="/Users/kevinmba/dev/cos", env=env
        )

        # Check the script ran successfully
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert "SUCCESS: message_format works without orjson" in result.stdout
