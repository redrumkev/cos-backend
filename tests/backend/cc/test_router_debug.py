import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestDebugLogRouter:
    """Integration tests for the /cc/debug/log endpoint."""

    async def test_debug_log_basic_event(self, test_client: "TestClient", db_session: AsyncSession) -> None:
        """Test basic debug log creation via API."""
        request_data: dict[str, Any] = {
            "event_type": "test_api_event",
            "payload": {"test_key": "test_value", "api": True},
            "prompt_data": {"prompt": "test prompt", "response": "test response"},
        }

        response = test_client.post("/cc/debug/log", json=request_data)

        assert response.status_code == 201
        result = response.json()

        # Validate response structure
        assert result["success"] is True
        assert "message" in result
        assert "log_ids" in result
        assert "performance_ms" in result
        assert isinstance(result["performance_ms"], int | float)

        # Validate log_ids structure
        log_ids = result["log_ids"]
        assert "base_log_id" in log_ids
        assert "event_log_id" in log_ids
        assert "prompt_trace_id" in log_ids

        # Validate UUIDs
        for log_id in log_ids.values():
            assert isinstance(log_id, str)
            # Validate UUID format
            uuid.UUID(log_id)

    async def test_debug_log_minimal_request(self, test_client: "TestClient", db_session: AsyncSession) -> None:
        """Test debug log with minimal required fields."""
        request_data: dict[str, Any] = {
            "event_type": "minimal_test",
        }

        response = test_client.post("/cc/debug/log", json=request_data)

        assert response.status_code == 201
        result = response.json()
        assert result["success"] is True
        assert "log_ids" in result

    async def test_debug_log_validation_error(self, test_client: "TestClient", db_session: AsyncSession) -> None:
        """Test validation error handling."""
        # Missing required event_type
        request_data: dict[str, Any] = {
            "payload": {"test": "data"},
        }

        response = test_client.post("/cc/debug/log", json=request_data)

        assert response.status_code == 422  # Validation error
        error_detail = response.json()
        assert "detail" in error_detail

    async def test_debug_log_with_custom_ids(self, test_client: "TestClient", db_session: AsyncSession) -> None:
        """Test debug log with custom request_id and trace_id."""
        custom_request_id = "custom-req-123"
        custom_trace_id = "trace-456"

        request_data: dict[str, Any] = {
            "event_type": "custom_ids_test",
            "request_id": custom_request_id,
            "trace_id": custom_trace_id,
            "payload": {"custom": True},
        }

        response = test_client.post("/cc/debug/log", json=request_data)

        assert response.status_code == 201
        result = response.json()
        assert result["success"] is True

    async def test_debug_log_performance_benchmark(
        self, test_client: "TestClient", db_session: AsyncSession, benchmark: Any
    ) -> None:
        """Benchmark debug log endpoint performance."""

        def _api_call() -> Any:
            request_data = {
                "event_type": "benchmark_test",
                "payload": {"benchmark": True, "iteration": 1},
            }
            response = test_client.post("/cc/debug/log", json=request_data)
            assert response.status_code == 201
            return response.json()

        result = benchmark.pedantic(_api_call, rounds=10, iterations=1)
        assert result["success"] is True
        # In unit test env with Redis circuit breaker open, performance can be degraded
        # Just ensure it completes within a reasonable timeout (5 seconds)
        assert result["performance_ms"] < 5000.0

    def test_debug_log_endpoint_exists(self, test_client: "TestClient") -> None:
        """Test that the debug log endpoint exists and responds to requests."""
        # Test with invalid data to ensure endpoint exists (should return 422, not 404)
        response = test_client.post("/cc/debug/log", json={})

        # Should be validation error (422), not not found (404)
        assert response.status_code == 422

        # Verify it's a validation error for missing event_type
        error_detail = response.json()
        assert "detail" in error_detail
        assert any("event_type" in str(error).lower() for error in error_detail["detail"])
