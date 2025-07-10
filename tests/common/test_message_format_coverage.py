"""Characterisation tests for message_format.py to achieve ≥95% coverage.

This module provides targeted tests for edge cases and specific code paths
to reach the required coverage threshold while maintaining test quality.
"""

import json
import uuid
from datetime import UTC, datetime, timezone
from unittest.mock import patch

import pytest

from src.common.message_format import EventType, build_message, parse_message
from src.core_v2.patterns.error_handling import COSError


class TestMessageFormatCoverage:
    """Test coverage for specific uncovered code paths in message_format.py."""

    def test_orjson_import_fallback(self) -> None:
        """Test the fallback when orjson import fails (lines 39-40)."""
        # This test demonstrates the module's behavior when orjson is not available
        # The ImportError scenario is triggered during module import, but we can test
        # that the code handles the HAS_ORJSON=False case properly

        # Test that message operations work even when orjson might not be available
        # by testing the standard json fallback path
        with patch("src.common.message_format.HAS_ORJSON", False):
            # Import the module functions again to trigger the fallback path
            from src.common.message_format import build_message as build_msg_fallback

            # Build a message without orjson
            message = build_msg_fallback(
                base_log_id=uuid.uuid4(),
                source_module="test.module",
                timestamp=datetime.now(UTC),
                trace_id="trace-123",
                request_id="req-456",
                event_type=EventType.PROMPT_TRACE,
                data={"test": "value"},
            )

            # Should still produce valid JSON
            assert isinstance(message, str)
            parsed = json.loads(message)
            assert parsed["source_module"] == "test.module"

    def test_timezone_conversion_line_195(self) -> None:
        """Test timezone conversion from non-UTC timezone (line 195)."""
        # Create a timestamp with a non-UTC timezone
        non_utc_timestamp = datetime.now(UTC).replace(tzinfo=UTC)
        # Convert to a different timezone (e.g., US Eastern)
        from datetime import timedelta

        eastern_tz = timezone(timedelta(hours=-5))
        eastern_timestamp = non_utc_timestamp.astimezone(eastern_tz)

        # Build message with non-UTC timestamp - this should trigger line 195
        message = build_message(
            base_log_id=uuid.uuid4(),
            source_module="test.module",
            timestamp=eastern_timestamp,  # Non-UTC timezone
            trace_id="trace-123",
            request_id="req-456",
            event_type=EventType.PROMPT_TRACE,
            data={"test": "value"},
        )

        # Should successfully convert and build message
        assert isinstance(message, str)
        parsed = json.loads(message)
        # Timestamp should be normalized to UTC with Z suffix
        assert parsed["timestamp"].endswith("Z")

    def test_cos_error_reraise_line_210(self) -> None:
        """Test COSError re-raise scenario in build_message (line 210)."""
        # Create a mock that raises a COSError to test the re-raise path
        with patch("src.common.message_format.MessageEnvelope") as mock_envelope:
            # Make the constructor raise a COSError
            from src.core_v2.patterns.error_handling import ErrorCategory

            original_cos_error = COSError(
                message="Test COSError",
                category=ErrorCategory.VALIDATION,
                details={"test": "error"},
            )
            mock_envelope.side_effect = original_cos_error

            # Call build_message - should re-raise the COSError directly
            with pytest.raises(COSError) as exc_info:
                build_message(
                    base_log_id=uuid.uuid4(),
                    source_module="test.module",
                    timestamp=datetime.now(UTC),
                    trace_id="trace-123",
                    request_id="req-456",
                    event_type=EventType.PROMPT_TRACE,
                    data={"test": "value"},
                )

            # Should be the same COSError instance (re-raised, not wrapped)
            assert exc_info.value is original_cos_error
            assert str(exc_info.value) == "Test COSError"

    def test_naive_timestamp_conversion(self) -> None:
        """Test naive timestamp (no timezone) conversion to UTC."""
        # Create a naive datetime (no timezone info)
        naive_timestamp = datetime(2025, 1, 1, 12, 0, 0)  # No timezone

        # Build message with naive timestamp - should trigger timezone assignment
        message = build_message(
            base_log_id=uuid.uuid4(),
            source_module="test.module",
            timestamp=naive_timestamp,  # Naive timestamp
            trace_id="trace-123",
            request_id="req-456",
            event_type=EventType.PROMPT_TRACE,
            data={"test": "value"},
        )

        # Should successfully assign UTC timezone and build message
        assert isinstance(message, str)
        parsed = json.loads(message)
        # Should have proper UTC format
        assert parsed["timestamp"].endswith("Z")

    def test_parse_message_with_orjson_fallback(self) -> None:
        """Test parse_message functionality with and without orjson."""
        # Create a valid message
        test_message = {
            "base_log_id": str(uuid.uuid4()),
            "source_module": "test.module",
            "timestamp": "2025-01-01T12:00:00.000000Z",
            "trace_id": "trace-123",
            "request_id": "req-456",
            "event_type": "prompt_trace",
            "data": {"test": "value"},
            "schema_version": 1,
        }

        # Test with orjson disabled
        with patch("src.common.message_format.HAS_ORJSON", False):
            message_str = json.dumps(test_message)
            envelope = parse_message(message_str)
            assert envelope.source_module == "test.module"
            assert envelope.event_type == EventType.PROMPT_TRACE

    def test_message_envelope_model_dump_json_error_handling(self) -> None:
        """Test error handling in MessageEnvelope.model_dump_json method."""
        from src.common.message_format import MessageEnvelope

        # Create a valid envelope
        envelope = MessageEnvelope(
            base_log_id=uuid.uuid4(),
            source_module="test.module",
            timestamp=datetime.now(UTC),
            trace_id="trace-123",
            request_id="req-456",
            event_type=EventType.PROMPT_TRACE,
            data={"test": "value"},
        )

        # Test that the model_dump_json method works normally
        json_str = envelope.model_dump_json()
        assert isinstance(json_str, str)
        assert "test.module" in json_str

        # Test error path by mocking model_dump to raise an exception
        with patch.object(envelope, "model_dump", side_effect=Exception("Test error")):
            with pytest.raises(COSError) as exc_info:
                envelope.model_dump_json()

            assert exc_info.value.category.value == "validation"
            assert "model_dump_json" in exc_info.value.details["operation"]
