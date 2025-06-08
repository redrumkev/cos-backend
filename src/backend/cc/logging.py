"""Async logging service for L1 memory layer.

This service provides high-performance async logging to PostgreSQL with Logfire integration,
request ID correlation, and transaction management optimized for Phase 2 operations.

Features:
- AsyncSession dependency injection with proper transaction management
- Logfire span integration with trace_id extraction and custom attributes
- Request ID context handling with UUID fallback
- Performance-optimized: P95 latency target < 2ms
- Comprehensive error handling with graceful degradation
"""

import asyncio
import uuid
from typing import Any

import logfire
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.request_id_middleware import get_request_id

_flush_lock = asyncio.Lock()


async def log_l1(
    db: AsyncSession,
    event_type: str,
    payload: dict[str, Any] | None = None,
    prompt_data: dict[str, Any] | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> dict[str, uuid.UUID]:
    """Asynchronously log data to L1 memory (mem0_cc schema).

    Args:
    ----
        db: AsyncSession for database operations
        event_type: Type of event being logged
        payload: Optional JSON-serializable payload for EventLog
        prompt_data: Optional prompt trace data for PromptTrace
        request_id: Request ID (will use from context if not provided)
        trace_id: Logfire trace ID (will attempt to get from current span if not provided)

    Returns:
    -------
        Dictionary with IDs of created records

    Performance:
        - Target P95 latency: < 2ms
        - Uses AsyncSession with optimized flush/commit patterns
        - Minimal Logfire overhead with graceful error handling

    """
    # Import models directly to avoid registry conflicts
    try:
        from src.backend.cc.mem0_models import BaseLog, EventLog, PromptTrace

        base_log_cls = BaseLog
        event_log_cls = EventLog
        prompt_trace_cls = PromptTrace
    except ImportError as err:
        # Fallback if import fails during testing - direct import preferred
        try:
            from src.backend.cc.mem0_models import BaseLog, EventLog, PromptTrace

            base_log_cls = BaseLog
            event_log_cls = EventLog
            prompt_trace_cls = PromptTrace
        except ImportError:
            raise ImportError("Failed to load mem0 models") from err

    # Get request_id from context if not provided
    if not request_id:
        request_id = get_request_id()
        if not request_id:
            request_id = str(uuid.uuid4())

    # Get trace_id from Logfire if not provided
    if not trace_id:
        try:
            current_span_func = getattr(logfire, "current_span", None)
            if current_span_func:
                current_span = current_span_func()
                if current_span and hasattr(current_span, "context"):
                    trace_id = str(current_span.context.trace_id)
        except (AttributeError, RuntimeError, ValueError):
            # Graceful degradation - continue without trace_id
            pass

    # Create base log record
    base_log = base_log_cls(level="INFO", message=f"Event: {event_type}", payload=payload or {})
    db.add(base_log)
    async with _flush_lock:
        await db.flush()  # Flush to get the ID without committing

    result_ids = {"base_log_id": base_log.id}

    # Create event log if payload provided
    if payload is not None:
        event_log = event_log_cls(
            event_type=event_type,
            event_data=payload,
            request_id=uuid.UUID(request_id) if isinstance(request_id, str) else request_id,
            trace_id=trace_id,
            base_log_id=base_log.id,
        )
        db.add(event_log)
        async with _flush_lock:
            await db.flush()
        result_ids["event_log_id"] = event_log.id

    # Create prompt trace if prompt_data provided
    if prompt_data is not None:
        prompt_trace = prompt_trace_cls(
            prompt_text=prompt_data.get("prompt_text", ""),
            response_text=prompt_data.get("response_text", ""),
            execution_time_ms=prompt_data.get("execution_time_ms", 0),
            token_count=prompt_data.get("token_count", 0),
            base_log_id=base_log.id,
        )
        db.add(prompt_trace)
        async with _flush_lock:
            await db.flush()
        result_ids["prompt_trace_id"] = prompt_trace.id

    # Add custom attributes to current Logfire span
    try:
        current_span_func = getattr(logfire, "current_span", None)
        if current_span_func:
            current_span = current_span_func()
            if current_span and hasattr(current_span, "set_attribute"):
                current_span.set_attribute("mem0.event_type", event_type)
                current_span.set_attribute("mem0.record_id", str(base_log.id))
                current_span.set_attribute("layer", "service")
    except (AttributeError, RuntimeError, ValueError):
        # Graceful degradation - span attributes are optional
        pass

    # Commit transaction to persist all records
    async with _flush_lock:
        await db.commit()
    return result_ids
