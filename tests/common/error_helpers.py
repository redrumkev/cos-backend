"""Error handling helpers for testing.

This module provides standardized error handling helpers to handle
ValidationError and other custom exceptions in tests.
"""

from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from src.core_v2.patterns.error_handling import ConflictError, COSError, NotFoundError, ValidationError


def validate_error_response(response: Any, expected_status: int, expected_detail: str) -> None:
    """Validate error response format.

    Args:
    ----
        response: HTTP response object
        expected_status: Expected HTTP status code
        expected_detail: Expected error detail message

    """
    assert response.status_code == expected_status
    error_data = response.json()
    assert "detail" in error_data
    assert error_data["detail"] == expected_detail


def validate_success_response(response: Any, expected_status: int = 200) -> dict[str, Any]:
    """Validate success response format.

    Args:
    ----
        response: HTTP response object
        expected_status: Expected HTTP status code (default: 200)

    Returns:
    -------
        dict: Response JSON data

    """
    assert response.status_code == expected_status
    json_data = response.json()
    return json_data if isinstance(json_data, dict) else {}


def convert_cos_error_to_http_exception(error: COSError) -> HTTPException:
    """Convert COS error to HTTPException for testing.

    Args:
    ----
        error: COS error instance

    Returns:
    -------
        HTTPException: FastAPI HTTP exception

    """
    if isinstance(error, ValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.user_message)
    elif isinstance(error, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.user_message)
    elif isinstance(error, ConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.user_message)
    else:
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error.user_message)


def create_error_response(error: COSError) -> JSONResponse:
    """Create JSON error response for testing.

    Args:
    ----
        error: COS error instance

    Returns:
    -------
        JSONResponse: FastAPI JSON response

    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(error, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(error, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, ConflictError):
        status_code = status.HTTP_409_CONFLICT

    return JSONResponse(status_code=status_code, content={"detail": error.user_message})


def setup_error_handlers(app: Any) -> dict[str, Any]:
    """Set up error handlers for testing.

    Args:
    ----
        app: FastAPI application instance

    Returns:
    -------
        dict: Dictionary containing the registered error handlers

    """

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Any, exc: ValidationError) -> JSONResponse:
        return create_error_response(exc)

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Any, exc: NotFoundError) -> JSONResponse:
        return create_error_response(exc)

    @app.exception_handler(ConflictError)
    async def conflict_error_handler(request: Any, exc: ConflictError) -> JSONResponse:
        return create_error_response(exc)

    @app.exception_handler(COSError)
    async def cos_error_handler(request: Any, exc: COSError) -> JSONResponse:
        return create_error_response(exc)

    return {
        "validation_handler": validation_error_handler,
        "not_found_handler": not_found_error_handler,
        "conflict_handler": conflict_error_handler,
        "cos_error_handler": cos_error_handler,
    }
