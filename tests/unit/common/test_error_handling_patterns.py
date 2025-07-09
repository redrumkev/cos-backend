"""Comprehensive test suite for error handling patterns.

This module provides comprehensive characterization tests for the error handling patterns
in src/core_v2/patterns/error_handling.py to achieve ≥95% coverage.

Pattern Reference: error_handling.py v2.1.0
Living Patterns System: Core pattern validation
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core_v2.patterns.error_handling import (
    ERROR_TO_STATUS,
    COSError,
    ErrorCategory,
    NotFoundError,
    UserService,
    ValidationError,
    error_handler,
    map_redis_error,
)


class TestErrorCategory:
    """Test ErrorCategory enum."""

    def test_error_category_values(self) -> None:
        """Test that ErrorCategory has expected values."""
        validation = "validation"
        not_found = "not_found"
        permission = "permission"
        conflict = "conflict"
        external_service = "external_service"
        internal = "internal"

        assert validation == ErrorCategory.VALIDATION
        assert not_found == ErrorCategory.NOT_FOUND
        assert permission == ErrorCategory.PERMISSION
        assert conflict == ErrorCategory.CONFLICT
        assert external_service == ErrorCategory.EXTERNAL_SERVICE
        assert internal == ErrorCategory.INTERNAL

    def test_error_category_str_behavior(self) -> None:
        """Test ErrorCategory string behavior."""
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.NOT_FOUND.value == "not_found"

    def test_error_category_comparison(self) -> None:
        """Test ErrorCategory comparison with strings."""
        # Test enum behavior
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.NOT_FOUND.value == "not_found"
        # Test comparison behavior
        validation_str = "validation"
        not_found_str = "not_found"
        assert validation_str == ErrorCategory.VALIDATION
        assert not_found_str != ErrorCategory.VALIDATION


class TestCOSError:
    """Test COSError base exception class."""

    def test_cos_error_initialization(self) -> None:
        """Test COSError initialization with all parameters."""
        error = COSError(
            message="Test error",
            category=ErrorCategory.VALIDATION,
            details={"field": "email"},
            user_message="Please check your email",
        )

        assert str(error) == "Test error"
        assert error.category == ErrorCategory.VALIDATION
        assert error.details == {"field": "email"}
        assert error.user_message == "Please check your email"

    def test_cos_error_minimal_initialization(self) -> None:
        """Test COSError with minimal parameters."""
        error = COSError(message="Test error", category=ErrorCategory.INTERNAL)

        assert str(error) == "Test error"
        assert error.category == ErrorCategory.INTERNAL
        assert error.details == {}
        assert error.user_message == "Test error"

    def test_cos_error_with_none_details(self) -> None:
        """Test COSError with None details."""
        error = COSError(message="Test error", category=ErrorCategory.INTERNAL, details=None)

        assert error.details == {}

    def test_cos_error_with_none_user_message(self) -> None:
        """Test COSError with None user_message."""
        error = COSError(message="Test error", category=ErrorCategory.INTERNAL, user_message=None)

        assert error.user_message == "Test error"

    def test_cos_error_is_exception(self) -> None:
        """Test that COSError is a proper exception."""
        error = COSError(message="Test error", category=ErrorCategory.INTERNAL)

        assert isinstance(error, Exception)

        # Test that it can be raised and caught
        with pytest.raises(COSError) as exc_info:
            raise error

        assert exc_info.value is error


class TestValidationError:
    """Test ValidationError subclass."""

    def test_validation_error_with_field(self) -> None:
        """Test ValidationError with field parameter."""
        error = ValidationError(message="Invalid email", field="email")

        assert str(error) == "Invalid email"
        assert error.category == ErrorCategory.VALIDATION
        assert error.details == {"field": "email"}
        assert error.user_message == "Invalid email"

    def test_validation_error_without_field(self) -> None:
        """Test ValidationError without field parameter."""
        error = ValidationError(message="Invalid input")

        assert str(error) == "Invalid input"
        assert error.category == ErrorCategory.VALIDATION
        assert error.details == {}
        assert error.user_message == "Invalid input"

    def test_validation_error_with_none_field(self) -> None:
        """Test ValidationError with None field."""
        error = ValidationError(message="Invalid input", field=None)

        assert error.details == {}

    def test_validation_error_with_additional_kwargs(self) -> None:
        """Test ValidationError with additional kwargs."""
        error = ValidationError(
            message="Invalid email",
            field="email",
            user_message="Please provide a valid email",
        )

        assert error.user_message == "Please provide a valid email"
        assert error.details == {"field": "email"}

    def test_validation_error_inheritance(self) -> None:
        """Test ValidationError inheritance."""
        error = ValidationError(message="Test", field="test")

        assert isinstance(error, COSError)
        assert isinstance(error, Exception)


class TestNotFoundError:
    """Test NotFoundError subclass."""

    def test_not_found_error_basic(self) -> None:
        """Test NotFoundError with basic parameters."""
        error = NotFoundError(resource="User", identifier=123)

        assert str(error) == "User with id 123 not found"
        assert error.category == ErrorCategory.NOT_FOUND
        assert error.details == {"resource": "User", "id": 123}
        assert error.user_message == "User with id 123 not found"

    def test_not_found_error_with_string_id(self) -> None:
        """Test NotFoundError with string identifier."""
        error = NotFoundError(resource="Document", identifier="doc-123")

        assert str(error) == "Document with id doc-123 not found"
        assert error.details == {"resource": "Document", "id": "doc-123"}

    def test_not_found_error_with_additional_kwargs(self) -> None:
        """Test NotFoundError with additional kwargs."""
        error = NotFoundError(
            resource="User",
            identifier=123,
            user_message="User not found in system",
        )

        assert error.user_message == "User not found in system"
        assert error.details == {"resource": "User", "id": 123}

    def test_not_found_error_inheritance(self) -> None:
        """Test NotFoundError inheritance."""
        error = NotFoundError(resource="User", identifier=123)

        assert isinstance(error, COSError)
        assert isinstance(error, Exception)


class TestErrorHandler:
    """Test error_handler context manager."""

    async def test_error_handler_success(self) -> None:
        """Test error_handler with successful operation."""
        logger = MagicMock()
        operation = "test_operation"

        async with error_handler(operation, logger):
            # No exception should be raised
            pass

        # Logger should not be called for successful operation
        logger.error.assert_not_called()

    async def test_error_handler_cos_error_reraise_true(self) -> None:
        """Test error_handler with COSError and reraise=True."""
        logger = MagicMock()
        operation = "test_operation"
        original_error = COSError(message="Test error", category=ErrorCategory.VALIDATION)

        with pytest.raises(COSError) as exc_info:
            async with error_handler(operation, logger, reraise=True):
                raise original_error

        assert exc_info.value is original_error
        logger.error.assert_called_once_with(f"{operation} failed with COS error", exc_info=True)

    async def test_error_handler_cos_error_reraise_false(self) -> None:
        """Test error_handler with COSError and reraise=False."""
        logger = MagicMock()
        operation = "test_operation"
        original_error = COSError(message="Test error", category=ErrorCategory.VALIDATION)

        # Should not raise exception
        async with error_handler(operation, logger, reraise=False):
            raise original_error

        logger.error.assert_called_once_with(f"{operation} failed with COS error", exc_info=True)

    async def test_error_handler_unexpected_error_reraise_true(self) -> None:
        """Test error_handler with unexpected error and reraise=True."""
        logger = MagicMock()
        operation = "test_operation"
        original_error = ValueError("Unexpected error")

        with pytest.raises(COSError) as exc_info:
            async with error_handler(operation, logger, reraise=True):
                raise original_error

        cos_error = exc_info.value
        assert str(cos_error) == "Unexpected error"
        assert cos_error.category == ErrorCategory.INTERNAL
        assert cos_error.details == {"operation": operation, "original_error": "ValueError"}
        assert cos_error.__cause__ is original_error

        logger.error.assert_called_once_with(f"{operation} failed with unexpected error", exc_info=True)

    async def test_error_handler_unexpected_error_reraise_false(self) -> None:
        """Test error_handler with unexpected error and reraise=False."""
        logger = MagicMock()
        operation = "test_operation"
        original_error = ValueError("Unexpected error")

        # Should not raise exception
        async with error_handler(operation, logger, reraise=False):
            raise original_error

        logger.error.assert_called_once_with(f"{operation} failed with unexpected error", exc_info=True)

    async def test_error_handler_default_reraise(self) -> None:
        """Test error_handler with default reraise behavior."""
        logger = MagicMock()
        operation = "test_operation"
        original_error = ValueError("Test error")

        # Default reraise should be True
        with pytest.raises(COSError):
            async with error_handler(operation, logger):
                raise original_error

    async def test_error_handler_operation_string_formatting(self) -> None:
        """Test error_handler with different operation strings."""
        logger = MagicMock()
        operations = ["fetch_user", "update_profile", "delete_account"]

        for operation in operations:
            logger.reset_mock()
            original_error = ValueError("Test error")

            with pytest.raises(COSError):
                async with error_handler(operation, logger):
                    raise original_error

            logger.error.assert_called_once_with(f"{operation} failed with unexpected error", exc_info=True)


class TestUserService:
    """Test UserService usage example."""

    def test_user_service_initialization(self) -> None:
        """Test UserService initialization."""
        db = MagicMock()
        logger = MagicMock()

        service = UserService(db, logger)

        assert service.db is db
        assert service.logger is logger

    async def test_user_service_get_user_success(self) -> None:
        """Test UserService.get_user with successful operation."""
        db = AsyncMock()
        logger = MagicMock()
        user_data = {"id": 123, "name": "John Doe"}

        db.fetch_user.return_value = user_data

        service = UserService(db, logger)
        result = await service.get_user(123)

        assert result == user_data
        db.fetch_user.assert_called_once_with(123)

    async def test_user_service_get_user_invalid_id(self) -> None:
        """Test UserService.get_user with invalid user ID."""
        db = AsyncMock()
        logger = MagicMock()

        service = UserService(db, logger)

        with pytest.raises(ValidationError) as exc_info:
            await service.get_user(0)

        error = exc_info.value
        assert str(error) == "User ID must be positive"
        assert error.details == {"field": "user_id"}

        # Should not call database for invalid ID
        db.fetch_user.assert_not_called()

    async def test_user_service_get_user_negative_id(self) -> None:
        """Test UserService.get_user with negative user ID."""
        db = AsyncMock()
        logger = MagicMock()

        service = UserService(db, logger)

        with pytest.raises(ValidationError) as exc_info:
            await service.get_user(-1)

        error = exc_info.value
        assert str(error) == "User ID must be positive"
        assert error.details == {"field": "user_id"}

    async def test_user_service_get_user_not_found(self) -> None:
        """Test UserService.get_user with user not found."""
        db = AsyncMock()
        logger = MagicMock()

        db.fetch_user.return_value = None

        service = UserService(db, logger)

        with pytest.raises(NotFoundError) as exc_info:
            await service.get_user(123)

        error = exc_info.value
        assert str(error) == "User with id 123 not found"
        assert error.details == {"resource": "User", "id": 123}

        db.fetch_user.assert_called_once_with(123)

    async def test_user_service_get_user_database_error(self) -> None:
        """Test UserService.get_user with database error."""
        db = AsyncMock()
        logger = MagicMock()

        db.fetch_user.side_effect = ConnectionError("Database connection failed")

        service = UserService(db, logger)

        with pytest.raises(COSError) as exc_info:
            await service.get_user(123)

        error = exc_info.value
        assert str(error) == "Database connection failed"
        assert error.category == ErrorCategory.INTERNAL
        assert error.details == {"operation": "get_user", "original_error": "ConnectionError"}

        # Check that the original error is preserved
        assert isinstance(error.__cause__, ConnectionError)


class TestErrorToStatus:
    """Test ERROR_TO_STATUS mapping."""

    def test_error_to_status_mapping(self) -> None:
        """Test that ERROR_TO_STATUS has correct mappings."""
        expected_mappings = {
            ErrorCategory.VALIDATION: 400,
            ErrorCategory.NOT_FOUND: 404,
            ErrorCategory.PERMISSION: 403,
            ErrorCategory.CONFLICT: 409,
            ErrorCategory.EXTERNAL_SERVICE: 502,
            ErrorCategory.INTERNAL: 500,
        }

        assert expected_mappings == ERROR_TO_STATUS

    def test_error_to_status_completeness(self) -> None:
        """Test that all error categories have status mappings."""
        error_categories = set(ErrorCategory)
        mapped_categories = set(ERROR_TO_STATUS.keys())

        assert error_categories == mapped_categories

    def test_error_to_status_values(self) -> None:
        """Test that status values are valid HTTP status codes."""
        valid_status_codes = {400, 403, 404, 409, 500, 502}
        actual_status_codes = set(ERROR_TO_STATUS.values())

        assert actual_status_codes == valid_status_codes


class TestMapRedisError:
    """Test map_redis_error function."""

    def test_map_redis_error_no_redis_import(self) -> None:
        """Test map_redis_error when Redis is not available."""
        original_error = ConnectionError("Redis not available")

        with patch.dict("sys.modules", {"redis.exceptions": None}):
            cos_error = map_redis_error(original_error)

        assert str(cos_error) == "Redis not available"
        assert cos_error.category == ErrorCategory.EXTERNAL_SERVICE
        assert cos_error.details == {"original_error": "ConnectionError"}

    def test_map_redis_error_authentication_error(self) -> None:
        """Test map_redis_error with AuthenticationError."""
        from redis.exceptions import AuthenticationError

        original_error = AuthenticationError("Authentication failed")
        cos_error = map_redis_error(original_error)

        assert str(cos_error) == "Redis authentication failed: Authentication failed"
        assert cos_error.category == ErrorCategory.PERMISSION
        assert cos_error.details == {"original_error": "AuthenticationError"}

    def test_map_redis_error_timeout_error(self) -> None:
        """Test map_redis_error with TimeoutError."""
        from redis.exceptions import TimeoutError as RedisTimeoutError

        original_error = RedisTimeoutError("Operation timed out")
        cos_error = map_redis_error(original_error)

        assert str(cos_error) == "Redis operation timeout: Operation timed out"
        assert cos_error.category == ErrorCategory.EXTERNAL_SERVICE
        assert cos_error.details == {"original_error": "TimeoutError", "timeout": True}

    def test_map_redis_error_response_error(self) -> None:
        """Test map_redis_error with ResponseError."""
        from redis.exceptions import ResponseError

        original_error = ResponseError("Invalid command")
        cos_error = map_redis_error(original_error)

        assert str(cos_error) == "Redis response error: Invalid command"
        assert cos_error.category == ErrorCategory.VALIDATION
        assert cos_error.details == {"original_error": "ResponseError"}

    def test_map_redis_error_connection_error(self) -> None:
        """Test map_redis_error with ConnectionError."""
        from redis.exceptions import ConnectionError as RedisConnectionError

        original_error = RedisConnectionError("Connection failed")
        cos_error = map_redis_error(original_error)

        assert str(cos_error) == "Redis connection error: Connection failed"
        assert cos_error.category == ErrorCategory.EXTERNAL_SERVICE
        assert cos_error.details == {"original_error": "ConnectionError"}

    def test_map_redis_error_busy_loading_error(self) -> None:
        """Test map_redis_error with BusyLoadingError."""
        from redis.exceptions import BusyLoadingError

        original_error = BusyLoadingError("Redis is loading")
        cos_error = map_redis_error(original_error)

        assert str(cos_error) == "Redis connection error: Redis is loading"
        assert cos_error.category == ErrorCategory.EXTERNAL_SERVICE
        assert cos_error.details == {"original_error": "BusyLoadingError"}

    def test_map_redis_error_unknown_error(self) -> None:
        """Test map_redis_error with unknown Redis error."""
        # Use a generic Redis exception that's not specifically handled
        original_error = Exception("Unknown Redis error")
        cos_error = map_redis_error(original_error)

        assert str(cos_error) == "Unknown Redis error"
        assert cos_error.category == ErrorCategory.EXTERNAL_SERVICE
        assert cos_error.details == {"original_error": "Exception"}

    def test_map_redis_error_import_error_fallback(self) -> None:
        """Test map_redis_error fallback when import fails."""
        original_error = ValueError("Some error")

        # Mock ImportError during import by removing the module
        with patch.dict("sys.modules", {"redis.exceptions": None}):
            cos_error = map_redis_error(original_error)

        assert str(cos_error) == "Some error"
        assert cos_error.category == ErrorCategory.EXTERNAL_SERVICE
        assert cos_error.details == {"original_error": "ValueError"}

    def test_map_redis_error_with_complex_error_message(self) -> None:
        """Test map_redis_error with complex error messages."""
        from redis.exceptions import AuthenticationError

        original_error = AuthenticationError("AUTH failed: invalid password")
        cos_error = map_redis_error(original_error)

        assert str(cos_error) == "Redis authentication failed: AUTH failed: invalid password"
        assert cos_error.category == ErrorCategory.PERMISSION
        assert cos_error.details == {"original_error": "AuthenticationError"}


class TestPatternVersionAndMarkers:
    """Test pattern version markers and documentation."""

    def test_pattern_version_marker_present(self) -> None:
        """Test that pattern version marker is present in module."""
        from src.core_v2.patterns import error_handling

        docstring = error_handling.__doc__
        assert "v2.1.0" in docstring
        assert "ADR-002" in docstring

    def test_pattern_docstring_structure(self) -> None:
        """Test that pattern docstring has required structure."""
        from src.core_v2.patterns import error_handling

        docstring = error_handling.__doc__
        assert "Purpose:" in docstring
        assert "When to use:" in docstring
        assert "When NOT to use:" in docstring

    def test_pattern_testing_approach_documented(self) -> None:
        """Test that testing approach is documented."""
        # Check that testing approach is documented in the source
        import inspect

        from src.core_v2.patterns import error_handling

        source = inspect.getsource(error_handling)
        assert "TESTING APPROACH" in source
        assert "pytest.raises" in source

    def test_pattern_migration_notes_documented(self) -> None:
        """Test that migration notes are documented."""
        import inspect

        from src.core_v2.patterns import error_handling

        source = inspect.getsource(error_handling)
        assert "MIGRATION NOTES" in source
        assert "To migrate existing error handling:" in source


class TestRealWorldScenarios:
    """Test real-world error handling scenarios."""

    async def test_nested_error_handling(self) -> None:
        """Test nested error handling scenarios."""
        logger = MagicMock()

        async def outer_operation() -> None:
            async with error_handler("outer", logger), error_handler("inner", logger):
                raise ValueError("Inner error")

        with pytest.raises(COSError) as exc_info:
            await outer_operation()

        # Should wrap the inner error
        error = exc_info.value
        assert error.category == ErrorCategory.INTERNAL
        assert error.details["operation"] == "inner"
        assert error.details["original_error"] == "ValueError"

    async def test_multiple_error_types_in_sequence(self) -> None:
        """Test handling multiple error types in sequence."""
        logger = MagicMock()

        # Test ValidationError first
        with pytest.raises(ValidationError):
            async with error_handler("validation", logger):
                raise ValidationError("Invalid input", field="email")

        # Test NotFoundError second
        with pytest.raises(NotFoundError):
            async with error_handler("not_found", logger):
                raise NotFoundError("User", 123)

        # Test generic error third
        with pytest.raises(COSError):
            async with error_handler("generic", logger):
                raise RuntimeError("Runtime error")

    async def test_error_context_preservation(self) -> None:
        """Test that error context is preserved through layers."""
        logger = MagicMock()

        async def database_layer() -> None:
            async with error_handler("database", logger):
                raise ConnectionError("Database connection failed")

        async def service_layer() -> None:
            async with error_handler("service", logger):
                await database_layer()

        async def api_layer() -> None:
            async with error_handler("api", logger):
                await service_layer()

        with pytest.raises(COSError) as exc_info:
            await api_layer()

        # Should preserve the original error context
        error = exc_info.value
        assert error.category == ErrorCategory.INTERNAL
        assert error.details["operation"] == "database"
        assert error.details["original_error"] == "ConnectionError"

    def test_error_chaining_with_cos_errors(self) -> None:
        """Test error chaining with COSError exceptions."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise COSError(
                    message="Wrapped error", category=ErrorCategory.INTERNAL, details={"wrapped": True}
                ) from e
        except COSError as cos_error:
            # Test that the chain is preserved
            assert cos_error.__cause__ is not None
            assert isinstance(cos_error.__cause__, ValueError)
            assert str(cos_error.__cause__) == "Original error"

    async def test_concurrent_error_handling(self) -> None:
        """Test error handling in concurrent scenarios."""
        logger = MagicMock()

        async def failing_task(task_id: int) -> None:
            async with error_handler(f"task_{task_id}", logger):
                if task_id % 2 == 0:
                    raise ValueError(f"Task {task_id} failed")
                else:
                    raise NotFoundError("Resource", task_id)

        # Run multiple tasks concurrently
        tasks = [failing_task(i) for i in range(4)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check that all tasks failed with appropriate errors
        for i, result in enumerate(results):
            assert isinstance(result, COSError)
            if i % 2 == 0:
                assert result.category == ErrorCategory.INTERNAL
                assert result.details["operation"] == f"task_{i}"
            else:
                assert result.category == ErrorCategory.NOT_FOUND
                assert result.details["resource"] == "Resource"
