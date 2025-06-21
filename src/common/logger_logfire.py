"""Logfire SDK integration module for COS with graceful degradation.

This module provides Logfire SDK integration with environment token handling,
graceful degradation when tokens are missing, and span utility functions.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import logfire as logfire_module
else:
    logfire_module = None

logger = logging.getLogger(__name__)

# Import logfire with graceful degradation
try:
    import logfire
except ImportError:
    # Graceful degradation when logfire is not available
    logger.warning("Logfire package not available. Tracing will be disabled.")
    logfire = None


def initialize_logfire() -> bool:
    """Initialize Logfire SDK with token from environment.

    Returns
    -------
        bool: True if successful, False otherwise.

    """
    token = os.environ.get("LOGFIRE_TOKEN")
    if not token:
        logger.warning("LOGFIRE_TOKEN not found in environment. Tracing disabled.")
        return False

    if logfire is None:
        logger.error("Failed to initialize Logfire: Logfire package not available")
        return False

    try:
        logfire.configure(service_name="cos-cc")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Logfire: {e}")
        return False


def add_span_attributes(attributes: dict[str, Any]) -> None:
    """Add custom attributes to the current Logfire span.

    Args:
    ----
        attributes: Dictionary of attributes to add to the current span.

    """
    if logfire is None:
        return

    try:
        # Use logfire context manager instead of current_span
        with logfire.span("add_attributes") as span:
            for key, value in attributes.items():
                span.set_attribute(key, value)
    except Exception as e:
        logger.error(f"Failed to add span attributes: {e}")


# Example usage and demonstration
def _demo() -> dict[str, Any]:
    """Demo function for testing Logfire integration."""
    return {
        "status": "logfire_ready" if logfire else "logfire_unavailable",
        "log_id": "logfire-demo-001",
        "memo": "Logfire integration test",
        "data": {"service": "cos-cc", "initialized": logfire is not None},
    }


if __name__ == "__main__":
    demo_result = _demo()
    logger.info(f"Demo Logfire integration result: {demo_result}")
