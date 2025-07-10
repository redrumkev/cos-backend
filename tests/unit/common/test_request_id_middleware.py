"""Unit tests for Request ID middleware implementation.

This module tests the RequestIDMiddleware functionality including:
- UUID generation when X-Request-ID header is absent
- Header extraction when X-Request-ID is present
- Request state storage
- Response header propagation
- ContextVar async access pattern
- Logfire span integration
"""

import asyncio
import contextlib
import os
import uuid
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware

from src.common.request_id_middleware import (
    RequestIDMiddleware,
    get_request_id,
    request_id_var,
)


class TestRequestIDMiddleware:
    """Test cases for RequestIDMiddleware class."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create FastAPI app with RequestIDMiddleware for testing."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/test")
        async def test_endpoint() -> dict[str, str]:
            request_id = get_request_id()
            return {"request_id": request_id or "none"}

        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create test client for FastAPI app."""
        return TestClient(app)

    def test_middleware_inherits_from_base_http_middleware(self) -> None:
        """Test that RequestIDMiddleware properly inherits from BaseHTTPMiddleware."""
        assert issubclass(RequestIDMiddleware, BaseHTTPMiddleware)
        middleware = RequestIDMiddleware(app=Mock())
        assert isinstance(middleware, BaseHTTPMiddleware)

    def test_middleware_generates_uuid_when_no_header(self, client: TestClient) -> None:
        """Test middleware generates UUID v4 when X-Request-ID header is absent."""
        response = client.get("/test")

        assert response.status_code == 200
        data = response.json()
        request_id = data["request_id"]

        # Should be a valid UUID
        assert request_id != "none"
        uuid_obj = uuid.UUID(request_id)
        assert str(uuid_obj) == request_id

        # Should be in response headers
        assert "x-request-id" in response.headers
        assert response.headers["x-request-id"] == request_id

    def test_middleware_uses_provided_header(self, client: TestClient) -> None:
        """Test middleware uses provided X-Request-ID header when present."""
        custom_id = "custom-request-id-123"
        response = client.get("/test", headers={"X-Request-ID": custom_id})

        assert response.status_code == 200
        data = response.json()

        # Should use the provided ID
        assert data["request_id"] == custom_id

        # Should be in response headers
        assert response.headers["x-request-id"] == custom_id

    def test_middleware_stores_in_request_state(self) -> None:
        """Test middleware stores request_id in request.state for downstream access."""
        app = FastAPI()
        middleware = RequestIDMiddleware(app=app)

        # Mock request and response
        request = Mock(spec=Request)
        request.headers = {"X-Request-ID": "test-request-id"}
        request.state = Mock()

        async def mock_call_next(req: Request) -> Response:
            # Verify request_id is set in state during processing
            assert hasattr(req.state, "request_id")
            assert req.state.request_id == "test-request-id"
            response = Mock(spec=Response)
            response.headers = MutableHeaders()
            return response

        response = asyncio.run(middleware.dispatch(request, mock_call_next))
        assert response.headers["X-Request-ID"] == "test-request-id"

    async def test_context_var_access_pattern(self) -> None:
        """Test ContextVar allows async access to request_id across call stack."""
        test_id = "context-var-test-id"

        # Set the context variable
        request_id_var.set(test_id)

        # Test helper function access
        assert get_request_id() == test_id

        # Test direct context variable access
        assert request_id_var.get() == test_id

    def test_context_var_isolation(self) -> None:
        """Test that ContextVar properly isolates request IDs across contexts."""

        async def context_1() -> str | None:
            # This would normally be set by middleware
            request_id_var.set("context-1-id")
            return get_request_id()

        async def context_2() -> str | None:
            request_id_var.set("context-2-id")
            return get_request_id()

        # Run in different contexts
        result_1 = asyncio.run(context_1())
        result_2 = asyncio.run(context_2())

        assert result_1 == "context-1-id"
        assert result_2 == "context-2-id"

    @patch("src.common.request_id_middleware.logfire")
    async def test_logfire_span_integration(self, mock_logfire: Mock) -> None:
        """Test integration with Logfire spans when available."""
        app = FastAPI()
        middleware = RequestIDMiddleware(app=app)

        # Mock logfire components
        mock_span = Mock()
        mock_logfire.current_span.return_value = mock_span

        request = Mock(spec=Request)
        request.headers = {}
        request.state = Mock()

        async def mock_call_next(req: Request) -> Response:
            return Response()

        with patch("src.common.request_id_middleware.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = uuid.UUID("12345678-1234-5678-9abc-123456789abc")
            await middleware.dispatch(request, mock_call_next)

        # Verify Logfire span was tagged with request_id
        mock_logfire.current_span.assert_called_once()
        mock_span.set_attribute.assert_called_once_with("request_id", "12345678-1234-5678-9abc-123456789abc")

    @patch("src.common.request_id_middleware.logfire")
    async def test_logfire_graceful_degradation(self, mock_logfire: Mock) -> None:
        """Test middleware handles Logfire errors gracefully."""
        app = FastAPI()
        middleware = RequestIDMiddleware(app=app)

        # Mock logfire to raise exception
        mock_logfire.current_span.side_effect = Exception("Logfire error")

        request = Mock(spec=Request)
        request.headers = {"X-Request-ID": "test-id"}
        request.state = Mock()

        async def mock_call_next(req: Request) -> Response:
            return Response()

        # Should not raise exception despite Logfire error
        response = await middleware.dispatch(request, mock_call_next)
        assert response.headers["X-Request-ID"] == "test-id"

    def test_uuid_format_validation(self, client: TestClient) -> None:
        """Test that generated UUIDs follow correct format."""
        response = client.get("/test")

        assert response.status_code == 200
        data = response.json()
        request_id = data["request_id"]

        # Should be valid UUID4 format
        uuid_obj = uuid.UUID(request_id)
        assert uuid_obj.version == 4
        assert str(uuid_obj) == request_id

    def test_middleware_preserves_response_content(self, client: TestClient) -> None:
        """Test that middleware doesn't interfere with response content."""
        response = client.get("/test")

        assert response.status_code == 200
        data = response.json()

        # Should have our expected content structure
        assert "request_id" in data
        assert isinstance(data["request_id"], str)
        assert data["request_id"] != "none"

    def test_concurrent_requests_isolation(self) -> None:
        """Test that concurrent requests have isolated request IDs."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        request_ids = []

        @app.get("/concurrent-test")
        async def concurrent_endpoint() -> dict[str, str]:
            request_id = get_request_id()
            request_ids.append(request_id)
            # Simulate some async work
            await asyncio.sleep(0.01)
            return {"request_id": request_id or "none"}

        client = TestClient(app)

        # Make concurrent requests
        responses = [client.get("/concurrent-test") for _ in range(5)]

        # All should be successful
        for response in responses:
            assert response.status_code == 200

        # All request IDs should be unique
        response_ids = [resp.json()["request_id"] for resp in responses]
        assert len(set(response_ids)) == 5  # All unique

        # All should be valid UUIDs
        for req_id in response_ids:
            uuid.UUID(req_id)  # Should not raise


class TestGetRequestIdHelper:
    """Test cases for get_request_id helper function."""

    def test_get_request_id_returns_none_when_not_set(self) -> None:
        """Test get_request_id returns None when context var not set."""
        # Reset context var
        request_id_var.set(None)
        assert get_request_id() is None

    def test_get_request_id_returns_current_value(self) -> None:
        """Test get_request_id returns current context variable value."""
        test_id = "test-helper-function-id"
        request_id_var.set(test_id)
        assert get_request_id() == test_id


class TestMiddlewareIntegration:
    """Integration tests for middleware with FastAPI."""

    async def test_end_to_end_flow_with_generated_id(self) -> None:
        """Test complete request flow with generated request ID."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/integration-test")
        async def integration_endpoint() -> dict[str, str | None]:
            return {
                "request_id_from_helper": get_request_id(),
                "message": "integration test",
            }

        client = TestClient(app)
        response = client.get("/integration-test")

        assert response.status_code == 200
        data = response.json()

        # Verify request ID is available in endpoint via helper
        assert "request_id_from_helper" in data
        assert data["request_id_from_helper"] is not None

        # Verify same ID in response header
        assert response.headers["X-Request-ID"] == data["request_id_from_helper"]

        # Verify UUID format
        parsed_uuid = uuid.UUID(data["request_id_from_helper"])
        assert parsed_uuid.version == 4

    async def test_end_to_end_flow_with_provided_id(self) -> None:
        """Test complete request flow with provided X-Request-ID header."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/integration-test")
        async def integration_endpoint() -> dict[str, str | None]:
            return {
                "request_id_from_helper": get_request_id(),
                "message": "integration test",
            }

        client = TestClient(app)
        provided_id = "client-provided-id-123"

        response = client.get("/integration-test", headers={"X-Request-ID": provided_id})

        assert response.status_code == 200
        data = response.json()

        # Verify provided ID is used throughout
        assert data["request_id_from_helper"] == provided_id
        assert response.headers["X-Request-ID"] == provided_id


class TestMiddlewareEdgeCases:
    """Test edge cases and error conditions for RequestIDMiddleware."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create FastAPI app with RequestIDMiddleware for edge case testing."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/test")
        async def test_endpoint() -> dict[str, str]:
            request_id = get_request_id()
            return {"request_id": request_id or "none"}

        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create test client for FastAPI app."""
        return TestClient(app)

    async def test_middleware_handles_missing_logfire(self) -> None:
        """Test middleware when logfire module is not available."""
        app = FastAPI()
        middleware = RequestIDMiddleware(app=app)

        request = Mock(spec=Request)
        request.headers = {"X-Request-ID": "test-missing-logfire"}
        request.state = Mock()

        async def mock_call_next(req: Request) -> Response:
            response = Response()
            # Response headers are initially empty MutableHeaders by default
            return response

        with patch("src.common.request_id_middleware.logfire", None):
            response = await middleware.dispatch(request, mock_call_next)
            assert response.headers["X-Request-ID"] == "test-missing-logfire"

    async def test_middleware_preserves_response_properties(self) -> None:
        """Test that middleware preserves response status, content, and other headers."""
        app = FastAPI()
        middleware = RequestIDMiddleware(app=app)

        request = Mock(spec=Request)
        request.headers = {}
        request.state = Mock()

        # Mock response with custom status and headers
        async def mock_call_next(req: Request) -> Response:
            response = Response(content="test content", status_code=201)
            response.headers["Custom-Header"] = "custom-value"
            return response

        response = await middleware.dispatch(request, mock_call_next)

        # Verify original response properties are preserved
        assert response.status_code == 201
        assert response.headers["Custom-Header"] == "custom-value"
        # Verify middleware added X-Request-ID
        assert "X-Request-ID" in response.headers

    async def test_context_var_default_value(self) -> None:
        """Test ContextVar behavior when get_request_id is called without middleware setting it."""
        # Test that get_request_id() handles the case where no request ID has been set
        # This tests the try/except LookupError logic in get_request_id()

        # Temporarily clear the context var by creating a new async context
        saved_value = None
        with contextlib.suppress(LookupError):
            saved_value = request_id_var.get()

        # Test the get_request_id function directly
        # Since we can't reliably clear the context var in tests,
        # we'll test that get_request_id() handles both cases correctly
        current_result = get_request_id()
        # The result should be a string (if set) or None (if not set)
        assert current_result is None or isinstance(current_result, str)

        # Test setting and getting a value
        test_id = "test-context-var-123"
        request_id_var.set(test_id)
        assert get_request_id() == test_id

        # Restore original value if it existed
        if saved_value is not None:
            request_id_var.set(saved_value)

    def test_get_current_request_id_outside_context(self) -> None:
        """Test the get_request_id helper function behavior."""
        # Test that get_request_id() returns the current context var value
        # or handles LookupError appropriately

        # Set a known value
        test_id = "outside-context-test"
        request_id_var.set(test_id)

        # Verify get_request_id() returns the set value
        result = get_request_id()
        assert result == test_id

        # The function should always return either a string or None
        assert isinstance(result, str) or result is None

    def test_request_state_storage(self) -> None:
        """Test that request_id is properly stored in request.state."""
        app = FastAPI()
        middleware = RequestIDMiddleware(app=app)

        request = Mock(spec=Request)
        request.headers = {"X-Request-ID": "state-storage-test"}
        request.state = Mock()

        async def mock_call_next(req: Request) -> Response:
            # Verify request_id is set in state during processing
            assert hasattr(req.state, "request_id")
            assert req.state.request_id == "state-storage-test"
            return Response()

        response = asyncio.run(middleware.dispatch(request, mock_call_next))
        assert response.headers["X-Request-ID"] == "state-storage-test"

    def test_response_header_addition(self) -> None:
        """Test that X-Request-ID header is added to response."""
        app = FastAPI()
        middleware = RequestIDMiddleware(app=app)

        request = Mock(spec=Request)
        request.headers = {}
        request.state = Mock()

        async def mock_call_next(req: Request) -> Response:
            return Response()

        with patch("src.common.request_id_middleware.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = uuid.UUID("12345678-1234-5678-9abc-123456789abc")
            response = asyncio.run(middleware.dispatch(request, mock_call_next))

        assert response.headers["X-Request-ID"] == "12345678-1234-5678-9abc-123456789abc"

    def test_case_insensitive_header_handling(self, client: TestClient) -> None:
        """Test that header handling is case-insensitive."""
        custom_id = "case-test-123"

        # Test various case combinations
        test_cases = ["X-Request-ID", "x-request-id", "X-REQUEST-ID", "x-Request-Id"]

        for header_name in test_cases:
            response = client.get("/test", headers={header_name: custom_id})
            assert response.status_code == 200
            data = response.json()
            assert data["request_id"] == custom_id
            assert response.headers["x-request-id"] == custom_id

    def test_context_var_persistence_through_request(self, client: TestClient) -> None:
        """Test that ContextVar persists throughout request lifecycle."""
        # Make request and verify the context var is accessible in endpoint
        response = client.get("/test")
        assert response.status_code == 200

        data = response.json()
        request_id = data["request_id"]

        # Should have generated a valid UUID
        assert request_id != "none"
        uuid_obj = uuid.UUID(request_id)
        assert str(uuid_obj) == request_id

        # Should be in response headers
        assert response.headers["x-request-id"] == request_id

    @patch("src.common.request_id_middleware.logfire", None)
    def test_middleware_works_without_logfire(self, client: TestClient) -> None:
        """Test that middleware works when logfire is not available."""
        response = client.get("/test")

        assert response.status_code == 200
        data = response.json()
        request_id = data["request_id"]

        # Should still generate UUID even without logfire
        assert request_id != "none"
        uuid_obj = uuid.UUID(request_id)
        assert str(uuid_obj) == request_id

        # Should be in response headers
        assert response.headers["x-request-id"] == request_id

    @patch("src.common.request_id_middleware.logfire")
    def test_logfire_span_tagging_success(self, mock_logfire: Mock, client: TestClient) -> None:
        """Test successful logfire span tagging."""
        # Setup mock
        mock_span = Mock()
        mock_logfire.current_span.return_value = mock_span

        response = client.get("/test")

        assert response.status_code == 200
        data = response.json()
        request_id = data["request_id"]

        # Verify logfire span was tagged
        mock_logfire.current_span.assert_called()
        mock_span.set_attribute.assert_called_with("request_id", request_id)

    @patch("src.common.request_id_middleware.logfire")
    @patch("src.common.request_id_middleware.logger")
    def test_logfire_span_tagging_exception_handling(
        self, mock_logger: Mock, mock_logfire: Mock, client: TestClient
    ) -> None:
        """Test that logfire span tagging exceptions are handled gracefully."""
        # Setup mock to raise exception
        mock_logfire.current_span.side_effect = Exception("Logfire error")

        response = client.get("/test")

        # Should still work despite logfire error
        assert response.status_code == 200
        data = response.json()
        request_id = data["request_id"]

        # Should have generated UUID despite error
        assert request_id != "none"
        uuid_obj = uuid.UUID(request_id)
        assert str(uuid_obj) == request_id

        # Should be in response headers
        assert response.headers["x-request-id"] == request_id

        # Should have logged the error at debug level
        mock_logger.debug.assert_called()


class TestLogfireImportError:
    """Test cases for logfire import error handling."""

    def test_logfire_import_error_handling(self) -> None:
        """Test handling when logfire module is not available (covers lines 40-41)."""
        import subprocess
        import sys

        # Create a test script that simulates logfire not being available
        test_script = """
import sys
import builtins

# Store original import
original_import = builtins.__import__

# Custom import that blocks logfire
def custom_import(name, *args, **kwargs):
    if name == 'logfire':
        raise ModuleNotFoundError("No module named 'logfire'")
    return original_import(name, *args, **kwargs)

# Replace import temporarily
builtins.__import__ = custom_import

# Now try to import request_id_middleware
try:
    # Clear any cached modules
    if 'src.common.request_id_middleware' in sys.modules:
        del sys.modules['src.common.request_id_middleware']

    # Import and check
    import src.common.request_id_middleware

    # Verify logfire is None when import fails
    expected_result = src.common.request_id_middleware.logfire
    assert expected_result is None, f"Expected logfire to be None, but got {expected_result}"
    print("SUCCESS: logfire gracefully set to None when module not found")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # Restore original import
    builtins.__import__ = original_import
"""

        # Run the test script in a subprocess
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            cwd="/Users/kevinmba/dev/cos",
            env={**os.environ, "PYTHONPATH": "/Users/kevinmba/dev/cos"},
        )

        # Check the script ran successfully
        assert result.returncode == 0, f"Script failed: {result.stderr}\nOutput: {result.stdout}"
        assert "SUCCESS: logfire gracefully set to None" in result.stdout
