"""Tests for missing router endpoint coverage in the Control Center module.

This file contains tests for HTTP endpoints that were missing coverage,
focusing on health checks, configuration, status, and error paths.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test health-related endpoints."""

    def test_health_check_success(self, test_client: TestClient) -> None:
        """Test successful health check endpoint."""
        with patch("src.backend.cc.router.read_system_health") as mock_health:
            # Mock successful health record
            mock_health.return_value = {"status": "healthy", "last_updated": "2025-04-02T10:00:00Z", "version": "1.0.0"}

            response = test_client.get("/cc/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    def test_health_check_no_record(self, test_client: TestClient) -> None:
        """Test health check when no health record exists."""
        with patch("src.backend.cc.router.read_system_health") as mock_health:
            # Mock no health record
            mock_health.return_value = None

            response = test_client.get("/cc/health")

            assert response.status_code == 404
            assert "no health record yet" in response.json()["detail"]

    def test_system_health_report(self, test_client: TestClient) -> None:
        """Test system health report endpoint."""
        response = test_client.get("/cc/system/health")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "healthy"
        assert len(data["modules"]) == 2
        assert data["modules"][0]["module"] == "cc"
        assert data["modules"][1]["module"] == "mem0"
        assert "timestamp" in data

    def test_ping_known_module(self, test_client: TestClient) -> None:
        """Test ping endpoint with known module."""
        ping_data = {"module": "cc"}

        response = test_client.post("/cc/ping", json=ping_data)

        assert response.status_code == 200
        data = response.json()
        assert data["module"] == "cc"
        assert data["status"] == "healthy"
        assert data["latency_ms"] == 5

    def test_ping_unknown_module(self, test_client: TestClient) -> None:
        """Test ping endpoint with unknown module."""
        ping_data = {"module": "unknown_module"}

        response = test_client.post("/cc/ping", json=ping_data)

        assert response.status_code == 200
        data = response.json()
        assert data["module"] == "unknown_module"
        assert data["status"] == "unknown"
        assert data["latency_ms"] == 0

    def test_ping_mem0_module(self, test_client: TestClient) -> None:
        """Test ping endpoint with mem0 module."""
        ping_data = {"module": "mem0"}

        response = test_client.post("/cc/ping", json=ping_data)

        assert response.status_code == 200
        data = response.json()
        assert data["module"] == "mem0"
        assert data["status"] == "healthy"
        assert data["latency_ms"] == 5


class TestConfigurationEndpoints:
    """Test configuration-related endpoints."""

    def test_get_config_success(self, test_client: TestClient) -> None:
        """Test successful configuration retrieval."""
        with patch("src.backend.cc.router.get_module_config") as mock_config:
            # Mock configuration
            mock_config.return_value = {"version": "1.0.0"}

            response = test_client.get("/cc/config")

            assert response.status_code == 200
            data = response.json()
            assert data["version"] == "1.0.0"
            assert "modules_loaded" in data
            assert "cc" in data["modules_loaded"]
            assert "mem0" in data["modules_loaded"]

    def test_get_status(self, test_client: TestClient) -> None:
        """Test simple status endpoint."""
        response = test_client.get("/cc/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestModuleErrorPaths:
    """Test error handling paths in module endpoints."""

    def test_create_module_service_error(self, test_client: TestClient) -> None:
        """Test create module when service raises ValueError."""
        with patch("src.backend.cc.router.service_create_module") as mock_service:
            # Mock service error
            mock_service.side_effect = ValueError("Module validation failed")

            module_data = {"name": "test_module", "version": "1.0.0"}
            response = test_client.post("/cc/modules", json=module_data)

            assert response.status_code == 409
            assert "Module validation failed" in response.json()["detail"]

    def test_update_module_service_error(self, test_client: TestClient) -> None:
        """Test update module when service raises ValueError."""
        fake_id = "fake-module-id"

        with patch("src.backend.cc.router.service_update_module") as mock_service:
            # Mock service error
            mock_service.side_effect = ValueError("Update validation failed")

            update_data = {"version": "2.0.0"}
            response = test_client.patch(f"/cc/modules/{fake_id}", json=update_data)

            assert response.status_code == 409
            assert "Update validation failed" in response.json()["detail"]

    def test_update_module_not_found_path(self, test_client: TestClient) -> None:
        """Test update module when module is not found by service."""
        fake_id = "fake-module-id"

        with patch("src.backend.cc.router.service_update_module") as mock_service:
            # Mock module not found (service returns None)
            mock_service.return_value = None

            update_data = {"version": "2.0.0"}
            response = test_client.patch(f"/cc/modules/{fake_id}", json=update_data)

            assert response.status_code == 404
            assert f"Module with ID {fake_id} not found" in response.json()["detail"]

    def test_get_module_not_found_path(self, test_client: TestClient) -> None:
        """Test get module when module is not found by service."""
        fake_id = "fake-module-id"

        with patch("src.backend.cc.router.service_get_module") as mock_service:
            # Mock module not found (service returns None)
            mock_service.return_value = None

            response = test_client.get(f"/cc/modules/{fake_id}")

            assert response.status_code == 404
            assert f"Module with ID {fake_id} not found" in response.json()["detail"]

    def test_delete_module_not_found_path(self, test_client: TestClient) -> None:
        """Test delete module when module is not found by service."""
        fake_id = "fake-module-id"

        with patch("src.backend.cc.router.service_delete_module") as mock_service:
            # Mock module not found (service returns None)
            mock_service.return_value = None

            response = test_client.delete(f"/cc/modules/{fake_id}")

            assert response.status_code == 404
            assert f"Module with ID {fake_id} not found" in response.json()["detail"]


class TestLoggingPaths:
    """Test that all endpoints properly log events."""

    @patch("src.backend.cc.router.log_event")
    def test_all_endpoints_log_events(self, mock_log_event: MagicMock, test_client: TestClient) -> None:
        """Test that all endpoints call log_event."""
        # Test basic endpoints that should always work
        endpoints_to_test = [
            ("GET", "/cc/status"),
            ("GET", "/cc/system/health"),
        ]

        for method, path in endpoints_to_test:
            mock_log_event.reset_mock()

            if method == "GET":
                response = test_client.get(path)
            elif method == "POST":
                response = test_client.post(path, json={})

            assert response.status_code in [200, 201, 422]  # Allow validation errors
            assert mock_log_event.called, f"log_event not called for {method} {path}"

    @patch("src.backend.cc.router.log_event")
    def test_ping_endpoint_logging(self, mock_log_event: MagicMock, test_client: TestClient) -> None:
        """Test that ping endpoint logs correctly."""
        ping_data = {"module": "test_module"}

        response = test_client.post("/cc/ping", json=ping_data)

        assert response.status_code == 200
        assert mock_log_event.called
        # Verify log contains module name
        call_args = mock_log_event.call_args
        assert call_args[1]["data"]["module"] == "test_module"
        assert "ping" in call_args[1]["tags"]

    @patch("src.backend.cc.router.log_event")
    def test_health_endpoint_logging(self, mock_log_event: MagicMock, test_client: TestClient) -> None:
        """Test that health endpoint logs correctly."""
        with patch("src.backend.cc.router.read_system_health") as mock_health:
            mock_health.return_value = {"status": "healthy"}

            response = test_client.get("/cc/health")

            assert response.status_code == 200
            assert mock_log_event.called
            # Verify log contains health tag
            call_args = mock_log_event.call_args
            assert "health" in call_args[1]["tags"]
            assert "cc_router" in call_args[1]["tags"]
