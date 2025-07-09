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
from datetime import UTC, datetime
from typing import Any

import logfire
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.common.logger import get_logger
from src.common.pubsub import get_pubsub
from src.common.request_id_middleware import get_request_id

_flush_lock = asyncio.Lock()
logger = get_logger(__name__)


async def _publish_l1_event(log_id: uuid.UUID, event_data: dict[str, Any]) -> None:
    """Publish L1 event to Redis after successful database commit with enhanced error handling.

    This function implements fire-and-forget publishing with comprehensive error isolation,
    Logfire integration, and graceful degradation. All exceptions are caught and logged
    but never re-raised to prevent interfering with the main database transaction flow.

    Args:
    ----
        log_id: UUID of the event log record
        event_data: Event data dictionary to publish

    """
    correlation_id = event_data.get("event", {}).get("request_id") or str(uuid.uuid4())

    # Check if event loop is running before attempting async operations
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # Event loop is not running (e.g., during teardown)
        logger.warning("Event loop not running, skipping Redis publish for log_id %s", log_id)
        return

    try:
        with logfire.span(
            "publish_l1_event", kind="producer", log_id=str(log_id), correlation_id=correlation_id
        ) as span:
            # Get Redis pubsub instance with circuit breaker protection
            pubsub = await get_pubsub()

            # Publish to the L1 Redis channel with correlation ID
            subscriber_count = await pubsub.publish("mem0.recorded.cc", event_data, correlation_id=correlation_id)

            # Set comprehensive span attributes for observability
            span.set_attribute("log_id", str(log_id))
            span.set_attribute("correlation_id", correlation_id)
            span.set_attribute("event_type", event_data.get("event", {}).get("event_type", "unknown"))
            span.set_attribute("subscriber_count", subscriber_count)
            span.set_attribute("success", True)

            # Log successful publish with detailed context
            logfire.info(
                "L1 event published successfully to Redis",
                log_id=str(log_id),
                correlation_id=correlation_id,
                channel="mem0.recorded.cc",
                subscriber_count=subscriber_count,
                event_type=event_data.get("event", {}).get("event_type", "unknown"),
            )

    except Exception as e:
        # Enhanced error isolation with comprehensive logging context
        error_context = {
            "log_id": str(log_id),
            "correlation_id": correlation_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "channel": "mem0.recorded.cc",
            "event_type": event_data.get("event", {}).get("event_type", "unknown"),
            "event_data_size": len(str(event_data)),
            "success": False,
        }

        # Log detailed error information
        logfire.error("Failed to publish L1 event to Redis - implementing graceful degradation", **error_context)

        # Additional logging for debugging in development
        logger.error(
            f"Redis publish failed for log_id {log_id}: {e}",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
                "event_data_keys": list(event_data.get("event", {}).keys()) if "event" in event_data else [],
            },
        )

        # Attempt graceful degradation - try fallback publish
        try:
            if hasattr(pubsub, "publish_with_fallback"):
                fallback_result = await pubsub.publish_with_fallback(
                    "mem0.recorded.cc", event_data, correlation_id=correlation_id, fallback_strategy="log_only"
                )

                logfire.info(
                    "L1 event fallback strategy applied",
                    log_id=str(log_id),
                    correlation_id=correlation_id,
                    fallback_result=fallback_result,
                )

        except Exception as fallback_error:
            # Even fallback failed - log but continue
            logfire.error(
                "L1 event fallback strategy also failed",
                log_id=str(log_id),
                correlation_id=correlation_id,
                fallback_error=str(fallback_error),
            )


@event.listens_for(Session, "after_commit", named=True)
def _after_commit_publish_events(session: Session, **kw: Any) -> None:
    """SQLAlchemy after_commit event listener for Redis publishing.

    This listener is triggered after a successful database commit and
    schedules Redis publishing tasks for any events in the session outbox.
    Uses asyncio.create_task for fire-and-forget execution.

    Args:
    ----
        session: The Session that was committed
        **kw: Additional event arguments (ignored)

    """
    # Retrieve and clear outbox events from session info
    outbox_events = session.info.pop("l1_outbox", None)
    if not outbox_events:
        return

    # Schedule publishing tasks asynchronously (fire-and-forget)
    try:
        loop = asyncio.get_running_loop()
        tasks = []
        for log_id, event_data in outbox_events:
            task = loop.create_task(_publish_l1_event(log_id, event_data))
            tasks.append(task)
    except RuntimeError:
        # No running event loop - this can happen in some test scenarios
        # Log the situation but don't fail
        logfire.warn("No running event loop for Redis publishing", event_count=len(outbox_events))


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
    from src.backend.cc.mem0_models import BaseLog, EventLog, PromptTrace

    base_log_cls = BaseLog
    event_log_cls = EventLog
    prompt_trace_cls = PromptTrace

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
        # Handle request_id conversion with validation
        try:
            if isinstance(request_id, str):
                # Try to parse as UUID, but fall back to generating new UUID if invalid
                try:
                    parsed_request_id = uuid.UUID(request_id)
                except ValueError:
                    # If request_id is not a valid UUID, generate a new one and log the original
                    parsed_request_id = uuid.uuid4()
                    logger.debug(
                        f"Invalid UUID format for request_id '{request_id}', generated new UUID: {parsed_request_id}"
                    )
            else:
                parsed_request_id = request_id
        except Exception:
            # Ultimate fallback - generate new UUID
            parsed_request_id = uuid.uuid4()

        event_log = event_log_cls(
            event_type=event_type,
            event_data=payload,
            request_id=parsed_request_id,
            trace_id=trace_id,
            base_log_id=base_log.id,
        )
        db.add(event_log)
        async with _flush_lock:
            await db.flush()
        result_ids["event_log_id"] = event_log.id

        # Queue event for Redis publishing after commit
        event_publish_data = {
            "log_id": str(event_log.id),
            "created_at": datetime.now(UTC).isoformat(),
            "event": {
                "event_type": event_type,
                "event_data": payload,
                "request_id": request_id,
                "trace_id": trace_id,
            },
        }

        # Add to session outbox for after_commit publishing
        if "l1_outbox" not in db.info:
            db.info["l1_outbox"] = []
        db.info["l1_outbox"].append((event_log.id, event_publish_data))

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
