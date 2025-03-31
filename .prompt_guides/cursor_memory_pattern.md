# Prompt Guide: Cursor Memory Logging Pattern

## Purpose
Instruct how to use `cursor_memory.py` to log prompt inputs, outputs, and model actions for traceability.

## Prompt Format
```
Whenever logging a prompt or LLM operation from Cursor, use:

```python
from cursor.cursor_memory import log_cursor_action

log_cursor_action(
    source="cursor",
    prompt="Refactor cc controller",
    result="Success: PR opened",
    notes="Used cc_module MDC"
)
```

This enables prompt tracing, failure analysis, and future refactor reviews.
```

## MDC Link
# MDC: cursor_logger
