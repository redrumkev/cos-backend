"""Tests for the Control Center main entry point.

This file contains tests for the CC main FastAPI application.
"""

# MDC: cc_module
from fastapi.testclient import TestClient

from src.backend.cc.cc_main import cc_app, cc_router


def test_cc_app_instance() -> None:
    """Test that the cc_app is a properly configured FastAPI instance."""
    # Check that cc_app has the expected properties
    assert cc_app.title == "Control Center API"
    assert cc_app.version == "0.1.0"
    assert cc_app.router.lifespan_context is not None


def test_cc_app_router() -> None:
    """Test that the cc_app includes the router with the correct prefix."""
    # Create a test client
    client = TestClient(cc_app)

    # Make a request to a known endpoint
    response = client.get("/cc/health")

    # Verify the response
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_cc_router_instance() -> None:
    """Test that the cc_router is a properly configured APIRouter instance."""
    # Check that cc_router is an APIRouter
    assert cc_router is not None

    # We can't directly check routes in an APIRouter, but we can verify it's not empty
    assert len(cc_router.routes) > 0
