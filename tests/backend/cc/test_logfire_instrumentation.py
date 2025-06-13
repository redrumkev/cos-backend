"""Tests for FastAPI Logfire auto-instrumentation functionality.

This module tests the Logfire integration in cc_main.py, including:
- Graceful degradation when Logfire is unavailable
- Graceful degradation when LOGFIRE_TOKEN is missing
- Successful instrumentation when properly configured
- Integration with FastAPI lifespan events
- Error handling and logging scenarios
"""

from __future__ import annotations

import logging
import os
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import the module under test
from src.backend.cc import cc_main


@pytest.fixture
def mock_logfire() -> MagicMock:
    """Mock logfire module for testing."""
    mock = MagicMock()
    mock.configure = MagicMock()
    mock.instrument_fastapi = MagicMock()
    return mock


@pytest.fixture
def clean_environment() -> Generator[None, None, None]:
    """Clean environment fixture that removes LOGFIRE_TOKEN."""
    original_token = os.environ.get("LOGFIRE_TOKEN")
    if "LOGFIRE_TOKEN" in os.environ:
        del os.environ["LOGFIRE_TOKEN"]

    yield

    if original_token is not None:
        os.environ["LOGFIRE_TOKEN"] = original_token


@pytest.fixture
def mock_environment_with_token() -> Generator[None, None, None]:
    """Mock environment with LOGFIRE_TOKEN set."""
    original_token = os.environ.get("LOGFIRE_TOKEN")
    os.environ["LOGFIRE_TOKEN"] = "test_token_12345"  # noqa: S105

    yield

    if original_token is not None:
        os.environ["LOGFIRE_TOKEN"] = original_token
    elif "LOGFIRE_TOKEN" in os.environ:
        del os.environ["LOGFIRE_TOKEN"]


class TestLogfireInitialization:
    """Test Logfire initialization functionality."""

    def test_initialize_logfire_when_unavailable(self, clean_environment: Any, caplog: Any) -> None:
        """Test initialization when logfire package is not available."""
        with (
            caplog.at_level(logging.INFO, logger="src.backend.cc.cc_main"),
            patch.object(cc_main, "_LOGFIRE_AVAILABLE", False),
        ):
            result = cc_main._initialize_logfire()

            assert result is False
            assert "Logfire not available, skipping initialization" in caplog.text

    def test_initialize_logfire_missing_token(
        self, mock_logfire: MagicMock, clean_environment: Any, caplog: Any
    ) -> None:
        """Test initialization when LOGFIRE_TOKEN is missing from environment."""
        with (
            caplog.at_level(logging.INFO, logger="src.backend.cc.cc_main"),
            patch.object(cc_main, "_LOGFIRE_AVAILABLE", True),
            patch.object(cc_main, "logfire_module", mock_logfire),
        ):
            result = cc_main._initialize_logfire()

            assert result is False
            assert "LOGFIRE_TOKEN not found in environment" in caplog.text
            mock_logfire.configure.assert_not_called()

    def test_initialize_logfire_success(
        self, mock_logfire: MagicMock, mock_environment_with_token: Any, caplog: Any
    ) -> None:
        """Test successful Logfire initialization."""
        with (
            caplog.at_level(logging.INFO, logger="src.backend.cc.cc_main"),
            patch.object(cc_main, "_LOGFIRE_AVAILABLE", True),
            patch.object(cc_main, "logfire_module", mock_logfire),
        ):
            result = cc_main._initialize_logfire()

            assert result is True
            assert "Logfire initialized successfully" in caplog.text
            mock_logfire.configure.assert_called_once_with(service_name="cos-cc")

    def test_initialize_logfire_configuration_error(
        self, mock_logfire: MagicMock, mock_environment_with_token: Any, caplog: Any
    ) -> None:
        """Test initialization when logfire.configure raises an exception."""
        mock_logfire.configure.side_effect = Exception("Configuration failed")

        with (
            caplog.at_level(logging.ERROR, logger="src.backend.cc.cc_main"),
            patch.object(cc_main, "_LOGFIRE_AVAILABLE", True),
            patch.object(cc_main, "logfire_module", mock_logfire),
        ):
            result = cc_main._initialize_logfire()

            assert result is False
            assert "Failed to initialize Logfire" in caplog.text
            assert "Configuration failed" in caplog.text


class TestFastAPIInstrumentation:
    """Test FastAPI instrumentation functionality."""

    def test_instrument_fastapi_app_when_unavailable(self, caplog: Any) -> None:
        """Test instrumentation when logfire package is not available."""
        app = FastAPI()

        with (
            caplog.at_level(logging.DEBUG, logger="src.backend.cc.cc_main"),
            patch.object(cc_main, "_LOGFIRE_AVAILABLE", False),
        ):
            result = cc_main._instrument_fastapi_app(app)

            assert result is False
            assert "Logfire not available, skipping FastAPI instrumentation" in caplog.text

    def test_instrument_fastapi_app_success(self, mock_logfire: MagicMock, caplog: Any) -> None:
        """Test successful FastAPI instrumentation."""
        app = FastAPI()

        with (
            caplog.at_level(logging.INFO, logger="src.backend.cc.cc_main"),
            patch.object(cc_main, "_LOGFIRE_AVAILABLE", True),
            patch.object(cc_main, "logfire_module", mock_logfire),
        ):
            result = cc_main._instrument_fastapi_app(app)

            assert result is True
            assert "FastAPI auto-instrumentation applied successfully" in caplog.text

            # Verify instrumentation was called with correct parameters
            mock_logfire.instrument_fastapi.assert_called_once()
            call_args = mock_logfire.instrument_fastapi.call_args

            # Check that app was passed as first argument
            assert call_args[0][0] is app

            # Check that excluded_urls and request_attributes_mapper were provided
            kwargs = call_args[1]
            assert "excluded_urls" in kwargs
            assert "request_attributes_mapper" in kwargs

            # Verify excluded URLs include health endpoints
            excluded_urls = kwargs["excluded_urls"]
            assert any("/health" in url for url in excluded_urls)
            assert any("/docs" in url for url in excluded_urls)

    def test_instrument_fastapi_app_error(self, mock_logfire: MagicMock, caplog: Any) -> None:
        """Test instrumentation when logfire.instrument_fastapi raises an exception."""
        app = FastAPI()
        mock_logfire.instrument_fastapi.side_effect = Exception("Instrumentation failed")

        with (
            caplog.at_level(logging.ERROR, logger="src.backend.cc.cc_main"),
            patch.object(cc_main, "_LOGFIRE_AVAILABLE", True),
            patch.object(cc_main, "logfire_module", mock_logfire),
        ):
            result = cc_main._instrument_fastapi_app(app)

            assert result is False
            assert "Failed to instrument FastAPI application" in caplog.text
            assert "Instrumentation failed" in caplog.text

    def test_request_attributes_mapper_functionality(self, mock_logfire: MagicMock) -> None:
        """Test the request attributes mapper function works correctly."""
        app = FastAPI()

        with patch.object(cc_main, "_LOGFIRE_AVAILABLE", True), patch.object(cc_main, "logfire_module", mock_logfire):
            cc_main._instrument_fastapi_app(app)

            # Get the mapper function
            call_args = mock_logfire.instrument_fastapi.call_args
            mapper = call_args[1]["request_attributes_mapper"]

            # Test mapper with mock request
            mock_request = Mock()
            mock_request.headers = {"user-agent": "test-agent"}
            mock_request.client = Mock(host="127.0.0.1")

            # Call with both request and attributes parameters
            mock_attributes: dict[str, Any] = {}
            result = mapper(mock_request, mock_attributes)

            # Verify the mapper returns a dictionary with expected keys
            assert isinstance(result, dict)
            assert "user_agent" in result
            assert "client_ip" in result
            assert result["user_agent"] == "test-agent"
            assert result["client_ip"] == "127.0.0.1"

    def test_request_attributes_mapper_missing_headers(self, mock_logfire: MagicMock) -> None:
        """Test the request attributes mapper handles missing headers gracefully."""
        app = FastAPI()

        with patch.object(cc_main, "_LOGFIRE_AVAILABLE", True), patch.object(cc_main, "logfire_module", mock_logfire):
            cc_main._instrument_fastapi_app(app)

            # Get the mapper function
            call_args = mock_logfire.instrument_fastapi.call_args
            mapper = call_args[1]["request_attributes_mapper"]

            # Test mapper with request missing headers
            mock_request = Mock()
            mock_request.headers = {}
            mock_request.client = None

            # Call with both parameters
            mock_attributes: dict[str, Any] = {}
            result = mapper(mock_request, mock_attributes)

            # Verify the mapper handles missing data gracefully
            assert isinstance(result, dict)
            assert result.get("user_agent") == "unknown"
            assert result.get("client_ip") == "unknown"


class TestLifespanIntegration:
    """Test lifespan integration functionality."""

    def test_lifespan_startup_with_logfire_available(
        self, mock_logfire: MagicMock, mock_environment_with_token: Any, caplog: Any
    ) -> None:
        """Test lifespan startup when Logfire is available and configured."""
        with (
            caplog.at_level(logging.INFO, logger="src.backend.cc.cc_main"),
            patch.object(cc_main, "_LOGFIRE_AVAILABLE", True),
            patch.object(cc_main, "logfire_module", mock_logfire),
        ):
            # Create a new app to trigger lifespan
            app = FastAPI()

            # Manually call the startup logic
            cc_main._initialize_logfire()
            cc_main._instrument_fastapi_app(app)

            # Verify both initialization and instrumentation were called
            mock_logfire.configure.assert_called_once_with(service_name="cos-cc")
            mock_logfire.instrument_fastapi.assert_called_once()

    def test_lifespan_startup_with_logfire_unavailable(self, clean_environment: Any, caplog: Any) -> None:
        """Test lifespan startup when Logfire is not available."""
        with (
            caplog.at_level(logging.INFO, logger="src.backend.cc.cc_main"),
            patch.object(cc_main, "_LOGFIRE_AVAILABLE", False),
        ):
            app = FastAPI()

            # Manually call the startup logic
            init_result = cc_main._initialize_logfire()
            instrument_result = cc_main._instrument_fastapi_app(app)

            # Verify graceful degradation
            assert init_result is False
            assert instrument_result is False
            assert "Logfire not available, skipping initialization" in caplog.text
            assert "Logfire not available, skipping FastAPI instrumentation" in caplog.text

    def test_lifespan_startup_partial_failure(
        self, mock_logfire: MagicMock, mock_environment_with_token: Any, caplog: Any
    ) -> None:
        """Test lifespan startup when initialization succeeds but instrumentation fails."""
        # Make instrumentation fail
        mock_logfire.instrument_fastapi.side_effect = Exception("Instrumentation error")

        with (
            caplog.at_level(logging.INFO, logger="src.backend.cc.cc_main"),
            patch.object(cc_main, "_LOGFIRE_AVAILABLE", True),
            patch.object(cc_main, "logfire_module", mock_logfire),
        ):
            app = FastAPI()

            # Call startup logic
            init_result = cc_main._initialize_logfire()
            instrument_result = cc_main._instrument_fastapi_app(app)

            # Verify partial success
            assert init_result is True
            assert instrument_result is False
            assert "Logfire initialized successfully" in caplog.text
            assert "Failed to instrument FastAPI application" in caplog.text


class TestIntegrationScenarios:
    """Test integration scenarios with the actual cc_app."""

    def test_cc_app_creation_with_logfire_available(
        self, mock_logfire: MagicMock, mock_environment_with_token: Any
    ) -> None:
        """Test that cc_app can be created successfully when Logfire is available."""
        with (
            patch.object(cc_main, "_LOGFIRE_AVAILABLE", True),
            patch.object(cc_main, "logfire_module", mock_logfire),
        ):
            # Import should work without errors
            from src.backend.cc.cc_main import cc_app

            assert cc_app is not None
            assert isinstance(cc_app, FastAPI)

    def test_cc_app_creation_with_logfire_unavailable(self, clean_environment: Any) -> None:
        """Test that cc_app can be created successfully when Logfire is not available."""
        with patch.object(cc_main, "_LOGFIRE_AVAILABLE", False):
            # Import should work without errors even when Logfire is unavailable
            from src.backend.cc.cc_main import cc_app

            assert cc_app is not None
            assert isinstance(cc_app, FastAPI)

    def test_cc_app_health_endpoint_functionality(
        self, mock_logfire: MagicMock, mock_environment_with_token: Any
    ) -> None:
        """Test that the health endpoint works correctly with Logfire instrumentation."""
        with (
            patch.object(cc_main, "_LOGFIRE_AVAILABLE", True),
            patch.object(cc_main, "logfire_module", mock_logfire),
        ):
            from src.backend.cc.cc_main import cc_app

            client = TestClient(cc_app)
            response = client.get("/health")

            # Health endpoint should work regardless of Logfire status
            assert response.status_code == 200

    def test_error_handling_preserves_app_functionality(
        self, mock_logfire: MagicMock, mock_environment_with_token: Any
    ) -> None:
        """Test that Logfire errors don't break the FastAPI application."""
        # Make both initialization and instrumentation fail
        mock_logfire.configure.side_effect = Exception("Config error")
        mock_logfire.instrument_fastapi.side_effect = Exception("Instrument error")

        with (
            patch.object(cc_main, "_LOGFIRE_AVAILABLE", True),
            patch.object(cc_main, "logfire_module", mock_logfire),
        ):
            from src.backend.cc.cc_main import cc_app

            # App should still be functional
            assert cc_app is not None
            assert isinstance(cc_app, FastAPI)

            # Health endpoint should still work
            client = TestClient(cc_app)
            response = client.get("/health")
            assert response.status_code == 200


# Test utilities and helpers
def test_logging_configuration() -> None:
    """Test that logging is properly configured for the module."""
    # Verify logger is created
    assert hasattr(cc_main, "logger")
    assert isinstance(cc_main.logger, logging.Logger)
    assert cc_main.logger.name == "src.backend.cc.cc_main"


# Import asyncio for async tests
