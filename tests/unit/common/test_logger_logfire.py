"""Comprehensive tests for src/common/logger_logfire.py module.

This file tests the Logfire SDK integration with graceful degradation,
environment token handling, and span utilities.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from src.common.logger_logfire import add_span_attributes, initialize_logfire


class TestInitializeLogfire:
    """Test initialize_logfire function thoroughly."""

    @patch.dict(os.environ, {"LOGFIRE_TOKEN": "test-token-12345"})
    @patch("src.common.logger_logfire.logfire.configure")
    def test_initialize_with_token_success(self, mock_configure: MagicMock) -> None:
        """Test successful initialization with valid token."""
        mock_configure.return_value = None

        result = initialize_logfire()

        assert result is True
        mock_configure.assert_called_once_with(service_name="cos-cc")

    @patch.dict(os.environ, {}, clear=True)  # No LOGFIRE_TOKEN
    @patch("src.common.logger_logfire.logger.warning")
    def test_initialize_without_token_graceful_degradation(self, mock_warning: MagicMock) -> None:
        """Test graceful degradation when LOGFIRE_TOKEN is missing."""
        result = initialize_logfire()

        assert result is False
        mock_warning.assert_called_once_with("LOGFIRE_TOKEN not found in environment. Tracing disabled.")

    @patch.dict(os.environ, {"LOGFIRE_TOKEN": ""})  # Empty token
    @patch("src.common.logger_logfire.logger.warning")
    def test_initialize_with_empty_token_graceful_degradation(self, mock_warning: MagicMock) -> None:
        """Test graceful degradation when LOGFIRE_TOKEN is empty."""
        result = initialize_logfire()

        assert result is False
        mock_warning.assert_called_once_with("LOGFIRE_TOKEN not found in environment. Tracing disabled.")

    @patch.dict(os.environ, {"LOGFIRE_TOKEN": "test-token"})
    @patch("src.common.logger_logfire.logfire.configure", side_effect=Exception("Config failed"))
    @patch("src.common.logger_logfire.logger.error")
    def test_initialize_with_token_but_config_fails(self, mock_error: MagicMock, mock_configure: MagicMock) -> None:
        """Test error handling when logfire.configure() raises an exception."""
        result = initialize_logfire()

        assert result is False
        mock_configure.assert_called_once_with(service_name="cos-cc")
        mock_error.assert_called_once_with("Failed to initialize Logfire: Config failed")

    @patch.dict(os.environ, {"LOGFIRE_TOKEN": "test-token"})
    @patch("src.common.logger_logfire.logfire.configure", side_effect=ImportError("Module not found"))
    @patch("src.common.logger_logfire.logger.error")
    def test_initialize_with_import_error(self, mock_error: MagicMock, mock_configure: MagicMock) -> None:
        """Test error handling when logfire module is not available."""
        result = initialize_logfire()

        assert result is False
        mock_error.assert_called_once_with("Failed to initialize Logfire: Module not found")


class TestAddSpanAttributes:
    """Test add_span_attributes function thoroughly."""

    @patch("src.common.logger_logfire.logfire.span")
    def test_add_span_attributes_success(self, mock_span_context: MagicMock) -> None:
        """Test successful addition of span attributes."""
        mock_span = MagicMock()
        mock_span_context.return_value.__enter__.return_value = mock_span

        attributes = {"user_id": "12345", "operation": "test", "count": 42}
        add_span_attributes(attributes)

        mock_span_context.assert_called_once_with("add_attributes")
        assert mock_span.set_attribute.call_count == 3
        mock_span.set_attribute.assert_any_call("user_id", "12345")
        mock_span.set_attribute.assert_any_call("operation", "test")
        mock_span.set_attribute.assert_any_call("count", 42)

    @patch("src.common.logger_logfire.logfire.span")
    def test_add_span_attributes_with_logfire_none(self, mock_span_context: MagicMock) -> None:
        """Test graceful handling when logfire is None."""
        with patch("src.common.logger_logfire.logfire", None):
            attributes = {"test": "value"}
            # Should not raise an exception
            add_span_attributes(attributes)

            mock_span_context.assert_not_called()

    @patch("src.common.logger_logfire.logfire.span")
    def test_add_span_attributes_empty_dict(self, mock_span_context: MagicMock) -> None:
        """Test handling of empty attributes dictionary."""
        mock_span = MagicMock()
        mock_span_context.return_value.__enter__.return_value = mock_span

        add_span_attributes({})

        mock_span_context.assert_called_once_with("add_attributes")
        mock_span.set_attribute.assert_not_called()

    @patch("src.common.logger_logfire.logfire.span", side_effect=Exception("Span error"))
    @patch("src.common.logger_logfire.logger.error")
    def test_add_span_attributes_exception_handling(self, mock_error: MagicMock, mock_span_context: MagicMock) -> None:
        """Test error handling when span context raises an exception."""
        attributes = {"test": "value"}

        # Should not raise an exception
        add_span_attributes(attributes)

        mock_span_context.assert_called_once_with("add_attributes")
        mock_error.assert_called_once_with("Failed to add span attributes: Span error")

    @patch("src.common.logger_logfire.logfire.span")
    def test_add_span_attributes_set_attribute_exception(self, mock_span_context: MagicMock) -> None:
        """Test error handling when set_attribute() raises an exception."""
        mock_span = MagicMock()
        mock_span.set_attribute.side_effect = Exception("Set attribute failed")
        mock_span_context.return_value.__enter__.return_value = mock_span

        attributes = {"test": "value"}

        with patch("src.common.logger_logfire.logger.error") as mock_error:
            # Should not raise an exception
            add_span_attributes(attributes)

            mock_error.assert_called_once_with("Failed to add span attributes: Set attribute failed")


class TestLoggerConfiguration:
    """Test logger configuration and setup."""

    def test_logger_is_configured(self) -> None:
        """Test that the logger is properly configured."""
        from src.common.logger_logfire import logger

        assert logger.name.startswith("src.common.logger_logfire")


class TestModuleImports:
    """Test module imports and dependencies."""

    def test_required_imports_available(self) -> None:
        """Test that all required imports are available."""
        # This will fail until we implement the module
        import src.common.logger_logfire

        assert hasattr(src.common.logger_logfire, "initialize_logfire")
        assert hasattr(src.common.logger_logfire, "add_span_attributes")
        assert hasattr(src.common.logger_logfire, "logger")

    def test_demo_function_exists(self) -> None:
        """Test that the demo function exists and works."""
        from src.common.logger_logfire import _demo

        result = _demo()
        assert isinstance(result, dict)
        assert "status" in result
        assert "log_id" in result
