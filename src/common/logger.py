"""Logger module - Shim for backwards compatibility.

DEPRECATION NOTICE:
This module now imports from core_v2.utils.logger as part of the
Strangler Fig migration pattern (ADR-001). This shim will be removed
in a future version once all imports have been updated.

Please update imports to use:
    from core_v2.utils.logger import get_logger, log_event, log_event_async

Instead of:
    from common.logger import get_logger, log_event, log_event_async
"""

# Import all exports from the new location
from core_v2.utils.logger import (
    _demo,
    get_logger,
    log_event,
    log_event_async,
    logger,
    mem,
)

# Re-export all symbols for backwards compatibility
__all__ = [
    "get_logger",
    "log_event",
    "log_event_async",
    "logger",
    "mem",
    "_demo",  # Also export _demo for test compatibility
]
