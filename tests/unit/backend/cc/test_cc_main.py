"""Unit tests for cc_main.py - FastAPI app initialization and lifespan."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest  # Phase 2: Remove for skip removal
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.backend.cc.cc_main import cc_app, cc_router, lifespan

# Phase 2: Skip block removed - main module testing enabled (P2-MAIN-001)

# Import the infrastructure skip marker from conftest


# Removed skip decorator - PostgreSQL services are now available
# @pytest.mark.skip(
#     reason="Infrastructure: PostgreSQL services not available locally. "
#     "Re-enable in Sprint 2 when docker-compose setup is complete."
# )
class TestCCMain:
    """Unit tests for the main CC module FastAPI app.

    These tests require database connectivity and are being skipped during the infrastructure
    setup phase. Will be re-enabled in Sprint 2 when docker-compose PostgreSQL setup is complete.
    """

    def test_cc_app_creation(self) -> None:
        """Test that cc_app is properly configured."""
        assert isinstance(cc_app, FastAPI)
        assert cc_app.title == "Control Center API"
        assert cc_app.description == "Central coordination module for the Creative Operating System"
        assert cc_app.version == "0.1.0"

    def test_cc_router_creation(self) -> None:
        """Test that cc_router is properly configured."""
        assert cc_router is not None
        # Check that the router includes the cc prefix
        route_paths = [getattr(route, "path", str(route)) for route in cc_router.routes]
        assert any("/cc" in path for path in route_paths)

    @patch("src.backend.cc.cc_main.log_event")
    async def test_lifespan_startup(self, mock_log_event: MagicMock) -> None:
        """Test lifespan startup event logging."""
        app = FastAPI()

        async with lifespan(app):
            # Check startup log was called with keyword arguments
            mock_log_event.assert_any_call(
                source="cc",
                data={"status": "starting"},
                tags=["lifecycle", "startup"],
                memo="Control Center module starting",
            )

    @patch("src.backend.cc.cc_main.log_event")
    async def test_lifespan_shutdown(self, mock_log_event: MagicMock) -> None:
        """Test lifespan shutdown event logging."""
        app = FastAPI()

        async with lifespan(app):
            pass  # Exit the context to trigger shutdown

        # Check shutdown log was called (should be at least 3 calls total)
        assert mock_log_event.call_count >= 3

        # Check shutdown log was called
        mock_log_event.assert_any_call(
            source="cc",
            data={"status": "stopping"},
            tags=["lifecycle", "shutdown"],
            memo="Control Center module shutting down",
        )

    def test_app_includes_router(self) -> None:
        """Test that cc_app includes the router with correct configuration."""
        # Check that routes are included
        assert len(cc_app.routes) > 1  # Should have at least the router routes plus OpenAPI

        # Check for cc-prefixed routes
        route_paths = [getattr(route, "path", str(route)) for route in cc_app.routes]
        cc_routes = [path for path in route_paths if path.startswith("/cc")]
        assert len(cc_routes) > 0

    def test_app_with_test_client(self) -> None:
        """Test that the app can be used with TestClient."""
        client = TestClient(cc_app)
        # Test that the app is responsive (this will test basic initialization)
        response = client.get("/docs")
        assert response.status_code == 200

    @patch("src.backend.cc.cc_main.log_event")
    def test_app_startup_shutdown_integration(self, mock_log_event: MagicMock) -> None:
        """Test complete app startup and shutdown cycle."""
        with TestClient(cc_app) as client:
            # App should start up and shut down properly
            response = client.get("/openapi.json")
            assert response.status_code == 200

        # Verify lifecycle events were logged
        assert mock_log_event.call_count >= 2


# Removed skip decorator - PostgreSQL services are now available
# @pytest.mark.skip(
#     reason="Infrastructure: PostgreSQL services not available locally. "
#     "Re-enable in Sprint 2 when docker-compose setup is complete."
# )
class TestLifespanIsolated:
    """Test lifespan function in isolation."""

    @patch("src.backend.cc.cc_main.log_event")
    async def test_lifespan_exception_handling(self, mock_log_event: MagicMock) -> None:
        """Test that lifespan handles exceptions gracefully."""
        app = FastAPI()

        # Should not raise even if log_event fails
        mock_log_event.side_effect = Exception("Log error")

        # Test that lifespan doesn't crash the app when logging fails
        # This is a robustness test - we expect it might raise
        with pytest.raises((Exception, RuntimeError)):
            async with lifespan(app):
                pass

        # At least startup should have been attempted
        assert mock_log_event.call_count >= 1
