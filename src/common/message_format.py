"""Standardized message format utilities for COS Redis communication.

This module provides a canonical message envelope format for high-performance
async communication between COS modules via Redis pub/sub. Designed for
sub-millisecond message creation with comprehensive validation.

Features:
- Type-safe Pydantic v2 models with orjson optimization
- RFC3339 timestamp formatting with millisecond precision
- Enum-based event type validation for L2 graph indexing
- Forward/backward compatibility via schema versioning
- Performance target: ≤ 50µs per message build

Pattern Reference: error_handling.py v2.1.0 (Living Patterns System)
Applied: COSError and error_handler context manager for structured error handling
Applied: Validation error handling with proper error categories
Applied: Graceful fallback for orjson serialization errors
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# Import error handling patterns
from src.core_v2.patterns.error_handling import COSError, ErrorCategory

logger = logging.getLogger(__name__)

# Try to import orjson for performance, fall back to standard json
try:
    import orjson

    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False


class EventType(str, Enum):
    """Enumerated event types for message classification and L2 graph indexing.

    These values are used by the L2 graph consumer for efficient O(1) filtering
    and routing of messages throughout the COS system.
    """

    PROMPT_TRACE = "prompt_trace"
    EVENT_LOG = "event_log"


class MessageEnvelope(BaseModel):
    """Canonical message envelope for COS Redis pub/sub communication.

    This envelope provides a standardized format for all inter-module communication,
    ensuring type safety, observability, and forward compatibility. All fields use
    snake_case naming for Python style consistency.

    The envelope is designed to be:
    - Lightweight (< 32kB for Redis compatibility)
    - Fast to serialize/deserialize (Pydantic v2 + orjson)
    - Future-proof (schema versioning)
    - Observable (trace_id correlation)

    Attributes
    ----------
        base_log_id: UUID of the originating log record
        source_module: Module that generated this message (e.g., "backend.cc.logging")
        timestamp: RFC3339 timestamp with millisecond precision and 'Z' suffix
        trace_id: OpenTelemetry trace ID for request correlation
        request_id: Request UUID for debugging and correlation
        event_type: Enumerated event type for efficient filtering
        data: Arbitrary domain payload (kept opaque for flexibility)
        schema_version: Message format version for compatibility

    """

    base_log_id: uuid.UUID
    source_module: str
    timestamp: datetime
    trace_id: str
    request_id: str
    event_type: EventType
    data: dict[str, Any]
    schema_version: int = Field(default=1, alias="_schema_version")

    model_config = {
        # Optimize for performance
        "validate_assignment": False,  # Skip validation on assignment for speed
        "extra": "allow",  # Allow extra fields for forward compatibility
        # JSON serialization settings for datetime and UUID
        "json_encoders": {
            datetime: lambda dt: dt.isoformat(timespec="microseconds").replace("+00:00", "Z"),
            uuid.UUID: str,
        },
    }

    def model_dump_json(self, **kwargs: Any) -> str:
        """Serialize to JSON string with optimal performance.

        Uses orjson if available for 2-3x faster serialization than standard
        json.dumps(). Falls back gracefully to Pydantic's default serialization.

        Returns
        -------
            JSON-encoded string ready for Redis pub/sub

        Raises
        ------
            COSError: When serialization fails with structured error details

        """
        try:
            if HAS_ORJSON:
                # Use orjson for maximum performance
                data = self.model_dump(by_alias=True, **kwargs)
                # Convert datetime to RFC3339 format
                if isinstance(data.get("timestamp"), datetime):
                    data["timestamp"] = data["timestamp"].isoformat(timespec="microseconds").replace("+00:00", "Z")
                # Convert UUID to string
                if isinstance(data.get("base_log_id"), uuid.UUID):
                    data["base_log_id"] = str(data["base_log_id"])
                json_bytes: bytes = orjson.dumps(data)
                return json_bytes.decode("utf-8")
            # Fall back to Pydantic's standard serialization
            return super().model_dump_json(by_alias=True, **kwargs)
        except Exception as e:
            # Convert any serialization error to COSError
            raise COSError(
                message=f"Failed to serialize MessageEnvelope to JSON: {e}",
                category=ErrorCategory.VALIDATION,
                details={"operation": "model_dump_json", "has_orjson": HAS_ORJSON, "original_error": type(e).__name__},
            ) from e


def build_message(
    *,
    base_log_id: uuid.UUID,
    source_module: str,
    timestamp: datetime,
    trace_id: str,
    request_id: str,
    event_type: EventType,
    data: dict[str, Any],
) -> str:
    """Build a standardized message envelope as a JSON string.

    This function creates a MessageEnvelope and immediately serializes it to JSON
    for optimal performance. The result is ready for Redis pub/sub publishing.

    Args:
    ----
        base_log_id: UUID of the originating log record
        source_module: Module that generated this message
        timestamp: Event timestamp (will be normalized to UTC with Z suffix)
        trace_id: OpenTelemetry trace ID for correlation
        request_id: Request UUID for debugging
        event_type: EventType enum value for filtering
        data: Arbitrary domain payload dictionary

    Returns:
    -------
        JSON-encoded string ready for Redis publishing

    Raises:
    ------
        COSError: When message building fails with structured error details

    Performance:
        Target: ≤ 50µs per call on modern hardware
        Uses Pydantic v2 + orjson for optimal speed

    Example:
    -------
        >>> import uuid
        >>> from datetime import datetime, timezone
        >>> json_str = build_message(
        ...     base_log_id=uuid.uuid4(),
        ...     source_module="backend.cc.logging",
        ...     timestamp=datetime.now(timezone.utc),
        ...     trace_id="otel-trace-123",
        ...     request_id="req-456",
        ...     event_type=EventType.PROMPT_TRACE,
        ...     data={"test": "value"}
        ... )

    """
    try:
        # Ensure timestamp is UTC for consistency
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        elif timestamp.tzinfo != UTC:
            timestamp = timestamp.astimezone(UTC)

        envelope = MessageEnvelope(
            base_log_id=base_log_id,
            source_module=source_module,
            timestamp=timestamp,
            trace_id=trace_id,
            request_id=request_id,
            event_type=event_type,
            data=data,
        )

        return envelope.model_dump_json()
    except COSError:
        # Re-raise COSError directly
        raise
    except Exception as e:
        # Convert other exceptions to COSError
        raise COSError(
            message=f"Failed to build message: {e}",
            category=ErrorCategory.VALIDATION,
            details={"operation": "build_message", "original_error": type(e).__name__},
        ) from e


def parse_message(raw: str | bytes) -> MessageEnvelope:
    """Parse and validate a message envelope from JSON string or bytes.

    This function deserializes and validates incoming messages from Redis pub/sub,
    ensuring type safety and data integrity throughout the system.

    Args:
    ----
        raw: JSON string or bytes from Redis pub/sub

    Returns:
    -------
        Validated MessageEnvelope instance

    Raises:
    ------
        COSError: When parsing fails with structured error details

    Example:
    -------
        >>> envelope = parse_message(json_str)
        >>> print(f"Event: {envelope.event_type}, Module: {envelope.source_module}")

    """
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")

        # Parse JSON to dict
        data = orjson.loads(raw) if HAS_ORJSON else json.loads(raw)

        # Handle field aliasing for backward compatibility
        if "_schema_version" in data and "schema_version" not in data:
            data["schema_version"] = data["_schema_version"]

        return MessageEnvelope.model_validate(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise COSError(
            message=f"Failed to parse message JSON: {e}",
            category=ErrorCategory.VALIDATION,
            details={"operation": "parse_message", "raw_type": type(raw).__name__, "has_orjson": HAS_ORJSON},
        ) from e
    except Exception as e:
        raise COSError(
            message=f"Failed to validate message envelope: {e}",
            category=ErrorCategory.VALIDATION,
            details={"operation": "parse_message", "original_error": type(e).__name__},
        ) from e
