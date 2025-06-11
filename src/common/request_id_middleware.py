"""Request ID middleware for FastAPI with traceability and async context support.

This module provides middleware to generate and manage request IDs for distributed tracing
across the COS system. It integrates with Logfire spans and provides async context access
via ContextVar for use throughout the request processing pipeline.

Features:
- UUID v4 generation when X-Request-ID header is absent
- Header extraction when X-Request-ID is present
- Request state storage for downstream access
- Response header propagation
- ContextVar async access pattern
- Logfire span integration with graceful degradation
"""

from __future__ import annotations

import importlib
import logging
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Logger for this module
logger = logging.getLogger(__name__)

# Attempt to import logfire; fallback to None if unavailable
try:
    logfire: Any | None = importlib.import_module("logfire")
except ModuleNotFoundError:
    logfire = None

# Context variable for async access to request ID across the entire request lifecycle
request_id_var: ContextVar[str | None] = ContextVar("request_id")


class RequestIDMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    """FastAPI middleware for request ID generation and management.

    This middleware handles:
    1. Extracting existing X-Request-ID from request headers
    2. Generating UUID v4 when no X-Request-ID is present
    3. Storing request_id in request.state for downstream access
    4. Setting request_id in ContextVar for async context access
    5. Tagging Logfire spans with request_id (if available)
    6. Adding X-Request-ID to response headers

    The middleware ensures request traceability across the entire request lifecycle
    while maintaining compatibility with existing X-Request-ID header conventions.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        """Process request with request ID generation and management."""
        # Extract existing request ID from header or generate new UUID v4
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store request ID in request.state for downstream access
        request.state.request_id = request_id

        # Set request ID in ContextVar for async context access
        request_id_var.set(request_id)

        # Tag current Logfire span with request_id (graceful degradation)
        if logfire is not None:
            try:
                current_span = getattr(logfire, "current_span", lambda: None)()
                if current_span and hasattr(current_span, "set_attribute"):
                    current_span.set_attribute("request_id", request_id)
            except Exception as exc:
                # Log at debug level; continue without interrupting request flow
                logger.debug("Logfire span tagging failed: %s", exc, exc_info=False)

        # Process the request through the rest of the middleware chain
        response: Response = await call_next(request)

        # Add request ID to response headers for client/downstream tracing
        response.headers["X-Request-ID"] = request_id

        return response


def get_request_id() -> str | None:
    """Return the current request ID from async context or ``None`` if unset."""
    try:
        return request_id_var.get()
    except LookupError:
        return None
