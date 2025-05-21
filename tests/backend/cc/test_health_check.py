"""Test the CC module health check and system health report endpoints."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from src.backend.cc.cc_main import cc_app
from src.backend.cc.schemas import HealthStatus, SystemHealthReport


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the CC module."""
    with TestClient(cc_app) as client_instance:
        yield client_instance


def test_health_check(client: TestClient) -> None:
    """Test the health check endpoint."""
    response = client.get("/cc/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    # Validate against Pydantic model
    health_status = HealthStatus(**data)
    assert health_status.status == "healthy"


def test_system_health_report(client: TestClient) -> None:
    """Test the system health report endpoint."""
    response = client.get("/cc/system/health")
    assert response.status_code == 200
    data = response.json()
    # Validate using Pydantic model
    system_report = SystemHealthReport(**data)
    assert system_report.overall_status == "healthy"
    assert len(system_report.modules) > 0
    assert system_report.timestamp is not None


def test_health_check_invalid_method(client: TestClient) -> None:
    """Test the health check endpoint using an invalid HTTP method (POST)."""
    response = client.post("/cc/health")
    # Depending on app implementation, might return 405 or 404.
    assert response.status_code in {404, 405}


def test_system_health_report_invalid_method(client: TestClient) -> None:
    """Test the system health report endpoint using an invalid HTTP method (PUT)."""
    response = client.put("/cc/system/health")
    # Depending on app routing, might return 405 or 404.
    assert response.status_code in {404, 405}


def test_non_existent_endpoint(client: TestClient) -> None:
    """Test accessing a non-existent endpoint returns 404."""
    response = client.get("/cc/nonexistent")
    assert response.status_code == 404
