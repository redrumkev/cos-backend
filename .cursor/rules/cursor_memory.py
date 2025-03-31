from typing import Any

from src.common.logger import log_event


def log_cursor_action(
    file: str,
    action: str,
    prompt: str,
    result: str | None = "",
    memo: str | None = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Log an action performed by Cursor on a file.

    Args:
    ----
        file (str): File path being worked on
        action (str): Type of operation (refactor, generate, etc.)
        prompt (str): Prompt sent to Cursor
        result (str): Output from Cursor (optional)
        memo (str): Additional notes or context (optional)
        tags (list): Optional tags for categorization

    Returns:
    -------
        dict: response from mem0 (typically dict[str, Any])

    """
    payload = {"file": file, "action": action, "prompt": prompt, "result": result}
    log_result: dict[str, Any] = log_event(
        source="cursor",
        data=payload,
        tags=tags or [action],
        memo=memo or f"Cursor {action} on {file}",
    )
    return log_result


# Optional demo
if __name__ == "__main__":
    log_result = log_cursor_action(
        file="backend/cc/router.py",
        action="refactor",
        prompt="Refactor this to use dependency injection",
        result="...refactored code...",
        tags=["refactor", "demo"],
        memo="Demo run for cursor memory",
    )
    print(f"Logged action: {log_result}")  # noqa: T201
