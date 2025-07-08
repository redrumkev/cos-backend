"""Pattern: Error Handling.

Version: 2025-07-08 (Initial - Pending Research)
ADR: ADR-002 (Pending)

Purpose: Standardize error handling across the COS system
When to use: All error scenarios in services, handlers, and utilities
When NOT to use: Low-level system errors that should bubble up
"""

import logging
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any


# CANONICAL IMPLEMENTATION
class ErrorCategory(str, Enum):
    """Standard error categories for consistent handling."""

    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    PERMISSION = "permission"
    CONFLICT = "conflict"
    EXTERNAL_SERVICE = "external_service"
    INTERNAL = "internal"


class COSError(Exception):
    """Base exception for all COS-specific errors."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        details: dict[str, Any] | None = None,
        user_message: str | None = None,
    ):
        super().__init__(message)
        self.category = category
        self.details = details or {}
        self.user_message = user_message or message


class ValidationError(COSError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None, **kwargs: Any) -> None:
        details = {"field": field} if field else {}
        super().__init__(message=message, category=ErrorCategory.VALIDATION, details=details, **kwargs)


class NotFoundError(COSError):
    """Raised when a requested resource doesn't exist."""

    def __init__(self, resource: str, identifier: Any, **kwargs: Any) -> None:
        super().__init__(
            message=f"{resource} with id {identifier} not found",
            category=ErrorCategory.NOT_FOUND,
            details={"resource": resource, "id": identifier},
            **kwargs,
        )


# ERROR CONTEXT MANAGER
@asynccontextmanager
async def error_handler(operation: str, logger: logging.Logger, reraise: bool = True):  # type: ignore[no-untyped-def]
    """Provide standard error handling context manager.

    Usage:
        async with error_handler("fetch_user", logger):
            user = await db.fetch_user(user_id)
    """
    try:
        yield
    except COSError:
        # Already handled, just log and reraise
        logger.error(f"{operation} failed with COS error", exc_info=True)
        if reraise:
            raise
    except Exception as e:
        # Wrap unexpected errors
        logger.error(f"{operation} failed with unexpected error", exc_info=True)
        if reraise:
            raise COSError(
                message=str(e),
                category=ErrorCategory.INTERNAL,
                details={"operation": operation, "original_error": type(e).__name__},
            ) from e


# USAGE EXAMPLE
class UserService:
    def __init__(self, db: Any, logger: logging.Logger):
        self.db = db
        self.logger = logger

    async def get_user(self, user_id: int) -> dict[str, Any]:
        """Get user by ID with error handling."""
        async with error_handler("get_user", self.logger):
            if user_id <= 0:
                raise ValidationError("User ID must be positive", field="user_id")

            user = await self.db.fetch_user(user_id)
            if not user:
                raise NotFoundError("User", user_id)

            return user  # type: ignore[no-any-return]


# HTTP ERROR MAPPING
ERROR_TO_STATUS = {
    ErrorCategory.VALIDATION: 400,
    ErrorCategory.NOT_FOUND: 404,
    ErrorCategory.PERMISSION: 403,
    ErrorCategory.CONFLICT: 409,
    ErrorCategory.EXTERNAL_SERVICE: 502,
    ErrorCategory.INTERNAL: 500,
}


# TESTING APPROACH
"""
async def test_error_handling():
    logger = logging.getLogger("test")

    # Test validation error
    with pytest.raises(ValidationError) as exc_info:
        async with error_handler("test_op", logger):
            raise ValidationError("Invalid input", field="email")

    assert exc_info.value.category == ErrorCategory.VALIDATION
    assert exc_info.value.details["field"] == "email"
"""

# MIGRATION NOTES
"""
To migrate existing error handling:
1. Replace generic exceptions with COSError subclasses
2. Add error categories for better handling
3. Use error_handler context manager in services
4. Map errors to HTTP status codes in handlers
5. Include structured details for debugging
"""

# TODO: Research and enhance with:
# - Error aggregation for bulk operations
# - Retry strategies for transient errors
# - Error reporting/monitoring integration
# - Internationalization for user messages
# - Stack trace sanitization for production
