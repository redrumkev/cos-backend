"""Test the CC module health check and system health report endpoints."""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.backend.cc.cc_main import cc_app
from src.common.database import get_async_db
from tests._utils.db_mocks import mock_execute


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the CC module."""
    with TestClient(cc_app) as client_instance:
        yield client_instance


@pytest.mark.usefixtures("mock_env_settings")
def test_health_check(client: TestClient) -> None:
    """Test the health check endpoint."""
    # Create a mock HealthStatus object that has the right attributes
    # This mimics the SQLAlchemy model
    mock_health_status = AsyncMock()
    mock_health_status.id = "123e4567-e89b-12d3-a456-426614174000"
    mock_health_status.module = "cc"
    mock_health_status.status = "healthy"
    mock_health_status.last_updated = "2025-01-01T12:00:00Z"
    mock_health_status.details = "All systems operational"

    # Mock the database session using proper mock helper
    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_execute(mock_health_status)

    # Override the database dependency
    async def mock_get_async_db() -> Any:
        yield mock_session

    try:
        # Apply the dependency override
        cc_app.dependency_overrides[get_async_db] = mock_get_async_db

        response = client.get("/cc/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "module" in data
        assert data["module"] == "cc"
    finally:
        # Clean up the override
        cc_app.dependency_overrides.clear()


@pytest.mark.usefixtures("mock_env_settings")
def test_system_health_report(client: TestClient) -> None:
    """Test the system health report endpoint."""
    # Mock the dependencies to prevent actual database connection attempts
    with (
        patch("src.backend.cc.deps.get_cc_db") as mock_get_db,
        patch("src.db.connection.get_async_engine") as mock_engine,
        patch("src.db.connection.get_async_session_maker") as mock_session_maker,
    ):
        # Configure the mocks
        mock_session = AsyncMock()

        # Mock the database query results
        mock_result = AsyncMock()
        mock_scalars = AsyncMock()
        mock_scalars.first = AsyncMock(return_value=None)  # No health status records
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        mock_async_context = AsyncMock()
        mock_async_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_async_context.__aexit__ = AsyncMock(return_value=None)

        # Mock get_cc_db to return the async context manager
        mock_get_db.return_value = mock_async_context

        # Mock the session maker to return a function that returns the async context
        mock_session_maker.return_value = lambda: mock_async_context
        mock_engine.return_value = AsyncMock()

        response = client.get("/cc/system/health")

        assert response.status_code == 200
        health_report = response.json()
        # The actual response format based on the error message
        assert "overall_status" in health_report
        assert "modules" in health_report
        assert "timestamp" in health_report
        assert health_report["overall_status"] in ["healthy", "degraded", "unhealthy"]


def test_health_check_invalid_method(client: TestClient) -> None:
    """Test the health check endpoint with invalid HTTP method."""
    response = client.post("/cc/health")
    assert response.status_code == 405


def test_system_health_report_invalid_method(client: TestClient) -> None:
    """Test the system health report endpoint with invalid HTTP method."""
    response = client.post("/cc/system/health")
    assert response.status_code == 405


def test_non_existent_endpoint(client: TestClient) -> None:
    """Test a non-existent endpoint."""
    response = client.get("/cc/non-existent")
    assert response.status_code == 404
