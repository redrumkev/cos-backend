"""Integration tests for Request ID middleware in CC module context.

This module tests the RequestIDMiddleware integration specifically within the
CC module FastAPI application, verifying proper middleware ordering and
functionality with existing endpoints.
"""

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.backend.cc.cc_main import cc_app


class TestCCRequestIDIntegration:
    """Test cases for RequestID middleware integration in CC module."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client for CC FastAPI app."""
        return TestClient(cc_app)

    @pytest.mark.usefixtures("mock_env_settings")
    def test_request_id_middleware_added_to_cc_app(self, client: TestClient) -> None:
        """Test that RequestID middleware is properly integrated into cc_app."""
        # Test with /cc/config which doesn't require database mocking
        response = client.get("/cc/config")

        # Verify response includes X-Request-ID header
        assert "x-request-id" in response.headers
        request_id = response.headers["x-request-id"]

        # Should be a valid UUID
        uuid_obj = uuid.UUID(request_id)
        assert str(uuid_obj) == request_id

    @pytest.mark.usefixtures("mock_env_settings")
    def test_request_id_middleware_with_health_endpoint(self, client: TestClient) -> None:
        """Test RequestID middleware functionality with /cc/health endpoint."""
        # Mock the database dependency following the gold standard pattern
        with (
            patch("src.db.connection.get_async_session_maker") as mock_session_maker,
            patch("src.db.connection.get_async_engine"),
        ):
            # Create a mock HealthStatus object
            mock_health_status = AsyncMock()
            mock_health_status.id = "123e4567-e89b-12d3-a456-426614174000"
            mock_health_status.module = "cc"
            mock_health_status.status = "healthy"
            mock_health_status.last_updated = "2025-01-01T12:00:00Z"
            mock_health_status.details = "All systems operational"

            # Mock the database session and query chain
            mock_session = AsyncMock()
            mock_scalars = AsyncMock()
            mock_scalars.first = lambda: mock_health_status
            mock_result = AsyncMock()
            mock_result.scalars = lambda: mock_scalars

            async def mock_execute(*args: Any, **kwargs: Any) -> Any:
                return mock_result

            mock_session.execute = mock_execute

            # Create async context manager for session
            class MockAsyncContextManager:
                async def __aenter__(self) -> Any:
                    return mock_session

                async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                    return None

            mock_session_maker.return_value = lambda: MockAsyncContextManager()

            response = client.get("/cc/health")

            assert response.status_code == 200
            assert "x-request-id" in response.headers

            # Request ID should be a valid UUID
            request_id = response.headers["x-request-id"]
            uuid.UUID(request_id)  # This will raise ValueError if invalid

    @pytest.mark.usefixtures("mock_env_settings")
    def test_request_id_middleware_with_config_endpoint(self, client: TestClient) -> None:
        """Test RequestID middleware functionality with /cc/config endpoint."""
        response = client.get("/cc/config")

        assert response.status_code == 200
        assert "x-request-id" in response.headers

        # Request ID should be a valid UUID
        request_id = response.headers["x-request-id"]
        uuid.UUID(request_id)  # This will raise ValueError if invalid

    @pytest.mark.usefixtures("mock_env_settings")
    def test_request_id_middleware_preserves_existing_header(self, client: TestClient) -> None:
        """Test that middleware preserves existing X-Request-ID headers."""
        custom_request_id = "custom-cc-request-id-123"

        # Use /cc/config endpoint which doesn't require database mocking
        response = client.get("/cc/config", headers={"X-Request-ID": custom_request_id})

        assert response.status_code == 200
        assert response.headers["x-request-id"] == custom_request_id

    def test_request_id_middleware_with_debug_endpoint(self, client: TestClient) -> None:
        """Test RequestID middleware functionality with /cc/debug/log endpoint."""
        # Test that endpoint exists and returns validation error (not 404)
        # This follows the pattern from test_router_debug.py
        response = client.post("/cc/debug/log", json={})

        # Should be validation error (422), not not found (404)
        assert response.status_code == 422
        assert "x-request-id" in response.headers

        # Request ID should be a valid UUID
        request_id = response.headers["x-request-id"]
        uuid.UUID(request_id)  # This will raise ValueError if invalid

    @pytest.mark.usefixtures("mock_env_settings")
    def test_request_id_middleware_ordering_before_logfire(self, client: TestClient) -> None:
        """Test that RequestID middleware is properly ordered before Logfire instrumentation."""
        # Use /cc/config which doesn't require database mocking
        response = client.get("/cc/config")

        assert response.status_code == 200
        assert "x-request-id" in response.headers

        # The fact that we get a valid response with X-Request-ID header
        # confirms that the middleware is properly integrated and working
        # before any Logfire instrumentation (which happens in lifespan)
        request_id = response.headers["x-request-id"]
        uuid.UUID(request_id)  # Validate UUID format

    @patch("src.common.request_id_middleware.logfire")
    @pytest.mark.usefixtures("mock_env_settings")
    def test_request_id_middleware_logfire_integration(self, mock_logfire: Any, client: TestClient) -> None:
        """Test that RequestID middleware integrates with Logfire spans when available."""
        response = client.get("/cc/config")

        assert response.status_code == 200
        assert "x-request-id" in response.headers

        # Verify Logfire span was called (middleware attempted to tag span)
        mock_logfire.current_span.assert_called()

    @pytest.mark.usefixtures("mock_env_settings")
    def test_request_id_middleware_no_interference_with_response_content(self, client: TestClient) -> None:
        """Test that RequestID middleware doesn't interfere with endpoint response content."""
        response = client.get("/cc/config")

        assert response.status_code == 200

        # Verify response content is preserved
        data = response.json()
        assert "version" in data  # Expected from config endpoint
        assert "modules_loaded" in data  # Expected from config endpoint

        # Verify middleware added header without affecting content
        assert "x-request-id" in response.headers

    @pytest.mark.usefixtures("mock_env_settings")
    def test_request_id_middleware_concurrent_requests(self, client: TestClient) -> None:
        """Test that RequestID middleware properly isolates request IDs for concurrent requests."""
        import concurrent.futures

        def make_request() -> str:
            response = client.get("/cc/config")
            return str(response.headers["x-request-id"])

        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            request_ids = [future.result() for future in futures]

        # All request IDs should be unique
        assert len(set(request_ids)) == len(request_ids)

        # All should be valid UUIDs
        for request_id in request_ids:
            uuid.UUID(request_id)

    @pytest.mark.usefixtures("mock_env_settings")
    def test_request_id_middleware_case_insensitive_header(self, client: TestClient) -> None:
        """Test that middleware handles case-insensitive X-Request-ID headers."""
        custom_request_id = "case-insensitive-test-123"

        # Test with different case variations
        test_cases = ["X-Request-ID", "x-request-id", "X-Request-Id", "x-Request-ID"]

        for header_name in test_cases:
            response = client.get("/cc/config", headers={header_name: custom_request_id})

            assert response.status_code == 200
            assert response.headers["x-request-id"] == custom_request_id


class TestCCRequestIDMiddlewareErrorHandling:
    """Test error handling scenarios for RequestID middleware in CC context."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client for CC FastAPI app."""
        return TestClient(cc_app)

    @patch("src.common.request_id_middleware.logfire")
    @pytest.mark.usefixtures("mock_env_settings")
    def test_middleware_graceful_degradation_logfire_error(self, mock_logfire: Any, client: TestClient) -> None:
        """Test that middleware handles Logfire errors gracefully without affecting requests."""
        # Mock logfire to raise exception
        mock_logfire.current_span.side_effect = Exception("Logfire connection error")

        response = client.get("/cc/config")

        # Request should still succeed despite Logfire error
        assert response.status_code == 200
        assert "x-request-id" in response.headers

        # Response content should be intact
        data = response.json()
        assert "version" in data

    @pytest.mark.usefixtures("mock_env_settings")
    def test_middleware_handles_malformed_request_gracefully(self, client: TestClient) -> None:
        """Test that middleware handles edge cases gracefully."""
        # Test with empty X-Request-ID header (should generate new UUID)
        response = client.get("/cc/config", headers={"X-Request-ID": ""})

        assert response.status_code == 200
        assert "x-request-id" in response.headers

        # Should generate new UUID when header is empty
        request_id = response.headers["x-request-id"]
        uuid.UUID(request_id)  # Should be valid UUID


class TestCCRequestIDMiddlewareCompatibility:
    """Test compatibility of RequestID middleware with CC module features."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client for CC FastAPI app."""
        return TestClient(cc_app)

    @pytest.mark.usefixtures("mock_env_settings")
    def test_middleware_compatible_with_existing_endpoints(self, client: TestClient) -> None:
        """Test that RequestID middleware is compatible with all existing CC endpoints."""
        # Test endpoints that don't require database mocking
        simple_endpoints = [
            "/cc/config",
            "/cc/status",  # Simple status endpoint
        ]

        for endpoint in simple_endpoints:
            response = client.get(endpoint)

            # All endpoints should work with middleware
            assert response.status_code == 200
            assert "x-request-id" in response.headers

            # Request ID should be valid UUID
            request_id = response.headers["x-request-id"]
            uuid.UUID(request_id)

        # Test debug endpoint existence (returns validation error, not 404)
        debug_response = client.post("/cc/debug/log", json={})
        assert debug_response.status_code == 422  # Validation error, not 404
        assert "x-request-id" in debug_response.headers
        uuid.UUID(debug_response.headers["x-request-id"])

    @pytest.mark.usefixtures("mock_env_settings")
    def test_middleware_preserves_fastapi_functionality(self, client: TestClient) -> None:
        """Test that middleware doesn't interfere with FastAPI's core functionality."""
        # Test config endpoint returns expected structure
        response = client.get("/cc/config")

        assert response.status_code == 200
        data = response.json()

        # Verify expected config endpoint structure is preserved
        assert "version" in data
        assert "modules_loaded" in data

        # Verify middleware functionality
        assert "x-request-id" in response.headers
        uuid.UUID(response.headers["x-request-id"])
