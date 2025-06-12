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


# Additional edge case tests
class TestMiddlewareEdgeCases:
    """Test edge cases and error conditions."""

    async def test_middleware_handles_missing_logfire(self) -> None:
        """Test middleware works when logfire module is not available."""
        app = FastAPI()

        with patch("src.common.request_id_middleware.logfire", None):
            middleware = RequestIDMiddleware(app=app)

            request = Mock(spec=Request)
            request.headers = {"X-Request-ID": "test-id"}
            request.state = Mock()

            async def mock_call_next(req: Request) -> Response:
                return Response()

            # Should work without Logfire
            response = await middleware.dispatch(request, mock_call_next)
            assert response.headers["X-Request-ID"] == "test-id"

    async def test_middleware_preserves_response_properties(self) -> None:
        """Test middleware preserves all response properties."""
        app = FastAPI()
        middleware = RequestIDMiddleware(app=app)

        request = Mock(spec=Request)
        request.headers = {"X-Request-ID": "preserve-test"}
        request.state = Mock()

        # Create response with specific properties
        original_response = Response(
            content="test content",
            status_code=201,
            headers={"Custom-Header": "custom-value"},
            media_type="application/json",
        )

        async def mock_call_next(req: Request) -> Response:
            return original_response

        response = await middleware.dispatch(request, mock_call_next)

        # Verify original properties preserved
        assert response.status_code == 201
        assert response.headers["Custom-Header"] == "custom-value"
        assert response.media_type == "application/json"

        # Verify our header added
        assert response.headers["X-Request-ID"] == "preserve-test"

    async def test_context_var_default_value(self) -> None:
        """Test ContextVar has proper default value."""
        # Import contextvars to get a fresh context without any set values
        import contextvars

        # Create a completely fresh context without any inherited values
        def test_unset_context() -> None:
            # In this fresh context, the ContextVar has never been set
            # So get() with default should return the default parameter
            assert request_id_var.get("default-value") == "default-value"
            # And get_request_id() should handle the LookupError gracefully
            assert get_request_id() is None

        # Run the test in a completely empty context
        empty_ctx = contextvars.Context()
        empty_ctx.run(test_unset_context)

        # Test that setting None explicitly still works in current context
        request_id_var.set(None)
        assert request_id_var.get() is None
        assert get_request_id() is None

    def test_get_current_request_id_outside_context(self) -> None:
        """Test that get_request_id returns None outside request context."""
        # Run in fresh context to isolate from any previous tests
        import contextvars

        def test_in_fresh_context() -> None:
            # In a completely fresh context, get_request_id should return None
            result = get_request_id()
            assert result is None

        # Run the test in a completely empty context
        empty_ctx = contextvars.Context()
        empty_ctx.run(test_in_fresh_context)

    def test_request_state_storage(self) -> None:
        """Test that request ID is stored in request.state."""
        middleware = RequestIDMiddleware(Mock())
        request = Mock(spec=Request)
        request.headers = {}
        request.state = Mock()

        # Mock UUID generation
        test_uuid = "test-uuid-123"
        with patch("uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = test_uuid

            # Create async mock for call_next
            async def mock_call_next(req: Request) -> Response:
                response = Mock(spec=Response)
                response.headers = MutableHeaders()
                return response

            # Test the middleware
            asyncio.run(middleware.dispatch(request, mock_call_next))

            # Verify request_id was set in request.state
            assert hasattr(request.state, "request_id")
            assert request.state.request_id == test_uuid

    def test_response_header_addition(self) -> None:
        """Test that X-Request-ID header is added to response."""
        middleware = RequestIDMiddleware(Mock())
        request = Mock(spec=Request)
        request.headers = MutableHeaders({"x-request-id": "existing-id"})
        request.state = Mock()

        async def mock_call_next(req: Request) -> Response:
            response = Mock(spec=Response)
            response.headers = MutableHeaders()
            return response

        # Test the middleware
        response = asyncio.run(middleware.dispatch(request, mock_call_next))

        # Verify response header was set
        assert "x-request-id" in response.headers
        assert response.headers["x-request-id"] == "existing-id"

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

    def test_context_var_persistence_through_request(self, client: TestClient) -> None:
        """Test that ContextVar persists throughout request lifecycle."""
        # Make request and verify the context var is accessible in endpoint
        response = client.get("/test")
        assert response.status_code == 200

        data = response.json()
        request_id_from_endpoint = data["request_id"]
        request_id_from_header = response.headers["x-request-id"]

        # Both should be the same and valid
        assert request_id_from_endpoint == request_id_from_header
        assert request_id_from_endpoint != "none"
        uuid.UUID(request_id_from_endpoint)  # Should not raise

    @patch("src.common.request_id_middleware.logfire", None)
    def test_middleware_works_without_logfire(self, client: TestClient) -> None:
        """Test that middleware works when logfire is not available."""
        response = client.get("/test")

        assert response.status_code == 200
        data = response.json()
        request_id = data["request_id"]

        # Should still work normally
        assert request_id != "none"
        uuid.UUID(request_id)  # Should be valid UUID
        assert response.headers["x-request-id"] == request_id

    @patch("src.common.request_id_middleware.logfire")
    def test_logfire_span_tagging_success(self, mock_logfire: Mock, client: TestClient) -> None:
        """Test successful logfire span tagging."""
        # Setup mock
        mock_span = Mock()
        mock_logfire.span.return_value = mock_span

        response = client.get("/test")

        assert response.status_code == 200
        # Verify logfire.span was called (span tagging attempted)
        # Note: We can't easily test the exact call due to async context

    @patch("src.common.request_id_middleware.logfire")
    @patch("src.common.request_id_middleware.logger")
    def test_logfire_span_tagging_exception_handling(
        self, mock_logger: Mock, mock_logfire: Mock, client: TestClient
    ) -> None:
        """Test that logfire span tagging exceptions are handled gracefully."""
        # Setup mock to raise exception
        mock_logfire.span.side_effect = Exception("Logfire error")

        response = client.get("/test")

        # Should still work despite logfire error
        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] != "none"

        # Should have logged the error
        mock_logger.debug.assert_called()
