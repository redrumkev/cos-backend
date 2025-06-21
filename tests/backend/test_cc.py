"""Tests for the Control Center (cc) API endpoints."""

# Standard library imports
from collections.abc import Generator

# Third-party imports
import pytest
from fastapi.testclient import TestClient

# Local imports
from backend.cc.cc_main import cc_app


@pytest.fixture(scope="module")
def module_client() -> Generator[TestClient, None, None]:
    """Create a TestClient instance specifically for the cc_app."""
    client = TestClient(cc_app)
    yield client
    # No cleanup needed for this simple fixture


def test_cc_status(module_client: TestClient) -> None:
    """Test the /status endpoint of the Control Center using module-specific client."""
    response = module_client.get("/cc/status")  # Correct path based on router prefix
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
