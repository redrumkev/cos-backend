"""Test error handling helpers."""

from unittest.mock import Mock

import pytest
from fastapi import HTTPException, status

from src.core_v2.patterns.error_handling import ConflictError, COSError, NotFoundError, ValidationError
from tests.common.error_helpers import (
    convert_cos_error_to_http_exception,
    create_error_response,
    validate_error_response,
    validate_success_response,
)


class TestErrorResponseValidation:
    """Test error response validation functions."""

    def test_validate_error_response_success(self) -> None:
        """Test successful error response validation."""
        response = Mock()
        response.status_code = 400
        response.json.return_value = {"detail": "Test error"}

        # Should not raise any exception
        validate_error_response(response, 400, "Test error")

    def test_validate_error_response_wrong_status(self) -> None:
        """Test error response validation with wrong status code."""
        response = Mock()
        response.status_code = 500
        response.json.return_value = {"detail": "Test error"}

        with pytest.raises(AssertionError):
            validate_error_response(response, 400, "Test error")

    def test_validate_error_response_wrong_detail(self) -> None:
        """Test error response validation with wrong detail."""
        response = Mock()
        response.status_code = 400
        response.json.return_value = {"detail": "Different error"}

        with pytest.raises(AssertionError):
            validate_error_response(response, 400, "Test error")

    def test_validate_success_response(self) -> None:
        """Test successful response validation."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"data": "test"}

        result = validate_success_response(response)
        assert result == {"data": "test"}

    def test_validate_success_response_custom_status(self) -> None:
        """Test successful response validation with custom status."""
        response = Mock()
        response.status_code = 201
        response.json.return_value = {"data": "test"}

        result = validate_success_response(response, 201)
        assert result == {"data": "test"}


class TestCOSErrorConversion:
    """Test COS error conversion functions."""

    def test_convert_validation_error(self) -> None:
        """Test ValidationError conversion to HTTPException."""
        error = ValidationError("Test validation error", field="test_field")

        http_exc = convert_cos_error_to_http_exception(error)

        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == status.HTTP_400_BAD_REQUEST
        assert http_exc.detail == error.user_message

    def test_convert_not_found_error(self) -> None:
        """Test NotFoundError conversion to HTTPException."""
        error = NotFoundError("User", "123")

        http_exc = convert_cos_error_to_http_exception(error)

        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == status.HTTP_404_NOT_FOUND
        assert http_exc.detail == error.user_message

    def test_convert_conflict_error(self) -> None:
        """Test ConflictError conversion to HTTPException."""
        error = ConflictError("User", "123")

        http_exc = convert_cos_error_to_http_exception(error)

        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == status.HTTP_409_CONFLICT
        assert http_exc.detail == error.user_message

    def test_convert_generic_cos_error(self) -> None:
        """Test generic COSError conversion to HTTPException."""
        from src.core_v2.patterns.error_handling import ErrorCategory

        error = COSError("Test error", ErrorCategory.INTERNAL, user_message="Internal server error")

        http_exc = convert_cos_error_to_http_exception(error)

        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert http_exc.detail == error.user_message

    def test_create_validation_error_response(self) -> None:
        """Test creating ValidationError JSON response."""
        error = ValidationError("Test validation error", field="test_field")

        response = create_error_response(error)

        assert response.status_code == 400
        assert response.body == b'{"detail":"Test validation error"}'

    def test_create_not_found_error_response(self) -> None:
        """Test creating NotFoundError JSON response."""
        error = NotFoundError("User", "123")

        response = create_error_response(error)

        assert response.status_code == 404
        body_content = response.body.decode() if isinstance(response.body, bytes) else str(response.body)
        assert "User with id 123 not found" in body_content

    def test_create_conflict_error_response(self) -> None:
        """Test creating ConflictError JSON response."""
        error = ConflictError("User", "123")

        response = create_error_response(error)

        assert response.status_code == 409
        body_content = response.body.decode() if isinstance(response.body, bytes) else str(response.body)
        assert "User with identifier 123 already exists" in body_content
