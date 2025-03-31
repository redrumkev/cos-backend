"""Tests for the Control Center router endpoints.

This file contains tests for the HTTP endpoints defined in the CC router.
"""

# MDC: cc_module
from collections.abc import Callable
from typing import TypeVar, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.backend.cc.deps import ModuleConfig, get_module_config
from src.backend.cc.router import router

T = TypeVar("T")
fixture = cast(Callable[[Callable[..., T]], Callable[..., T]], pytest.fixture)


@fixture
def client() -> TestClient:
    """Create a test client for the router."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    """Test the health check endpoint."""
    # Make a request to the health endpoint
    response = client.get("/health")

    # Verify the response status code
    assert response.status_code == 200

    # Verify the response content
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_get_config(client: TestClient) -> None:
    """Test the configuration endpoint."""
    # Define the mock config data
    mock_config_data = {
        "version": "0.1.0",
        "environment": "test",
    }

    # Define an override function for the dependency
    def override_get_module_config() -> ModuleConfig:
        return mock_config_data

    app = cast(FastAPI, client.app)  # Add this line to properly type the app
    app.dependency_overrides[get_module_config] = override_get_module_config

    try:
        response = client.get("/config")

        # Verify the response status code
        assert response.status_code == 200

        # Verify the response content includes the expected keys
        data = response.json()
        assert "version" in data
        assert "modules_loaded" in data

        # Check that version matches our mock data
        assert data["version"] == mock_config_data["version"]

    finally:
        app.dependency_overrides.clear()  # Better than del for cleanup


def test_system_health_report(client: TestClient) -> None:
    """Test the system health report endpoint."""
    # Make a request to the system health endpoint
    response = client.get("/system/health")

    # Verify the response status code
    assert response.status_code == 200

    # Verify the response content
    data = response.json()
    assert "overall_status" in data
    assert "modules" in data
    assert "timestamp" in data
    assert isinstance(data["modules"], list)
    assert len(data["modules"]) > 0

    # Verify module data structure
    module = data["modules"][0]
    assert "module" in module
    assert "status" in module
    assert "last_updated" in module


def test_ping_module(client: TestClient) -> None:
    """Test the ping module endpoint."""
    # Test data
    request_data = {"module": "cc"}

    # Make a request to the ping endpoint
    response = client.post("/ping", json=request_data)

    # Verify the response status code
    assert response.status_code == 200

    # Verify the response content
    data = response.json()
    assert "module" in data
    assert "status" in data
    assert "latency_ms" in data
    assert data["module"] == "cc"
    assert data["status"] == "healthy"


def test_ping_unknown_module(client: TestClient) -> None:
    """Test the ping module endpoint with an unknown module."""
    # Test data
    request_data = {"module": "unknown_module"}

    # Make a request to the ping endpoint
    response = client.post("/ping", json=request_data)

    # Verify the response status code
    assert response.status_code == 200

    # Verify the response content
    data = response.json()
    assert data["module"] == "unknown_module"
    assert data["status"] == "unknown"
    assert data["latency_ms"] == 0
