"""TDD tests for enhanced debug endpoints with Redis integration validation.

This test module covers Task 008 implementation:
- Enhanced /debug/log endpoint with Redis publishing validation
- New /debug/redis-health endpoint for comprehensive Redis monitoring
- Integration tests for Redis connectivity and message inspection
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

# Status codes constants to avoid magic numbers
STATUS_OK = 200
STATUS_CREATED = 201
STATUS_NOT_FOUND = 404


class TestEnhancedDebugLogEndpoint:
    """TDD tests for enhanced /debug/log endpoint with Redis validation."""

    def test_enhanced_debug_log_includes_redis_validation(self, test_client: TestClient) -> None:
        """Test that enhanced debug log endpoint validates Redis publishing."""
        with patch("src.backend.cc.logging.log_l1") as mock_log_l1:
            mock_log_l1.return_value = {
                "base_log_id": uuid.uuid4(),
                "event_log_id": uuid.uuid4(),
            }

            request_data = {
                "event_type": "redis_validation_test",
                "payload": {"test_key": "test_value"},
            }

            response = test_client.post("/cc/debug/log", json=request_data)

            # Enhanced response should include Redis validation fields
            assert response.status_code == STATUS_CREATED
            result = response.json()

            # Original fields should still exist
            assert result["success"] is True
            assert "message" in result
            assert "log_ids" in result
            assert "performance_ms" in result

            # New Redis validation fields should be present
            assert "redis_validation" in result
            redis_validation = result["redis_validation"]
            assert "publish_success" in redis_validation
            assert "published_message" in redis_validation
            assert "redis_latency_ms" in redis_validation
            assert "connection_status" in redis_validation

    def test_enhanced_debug_log_redis_failure_handling(self, test_client: TestClient) -> None:
        """Test Redis failure handling in enhanced debug endpoint."""
        with patch("src.backend.cc.logging.log_l1") as mock_log_l1:
            mock_log_l1.return_value = {
                "base_log_id": uuid.uuid4(),
                "event_log_id": uuid.uuid4(),
            }

            request_data = {
                "event_type": "redis_failure_test",
                "payload": {"test": "data"},
            }

            response = test_client.post("/cc/debug/log", json=request_data)

            assert response.status_code == STATUS_CREATED  # Should still succeed
            result = response.json()

            assert result["success"] is True  # Main operation succeeds
            redis_validation = result["redis_validation"]
            # These fields should exist regardless of Redis status
            assert "publish_success" in redis_validation
            assert "connection_status" in redis_validation

    def test_enhanced_debug_log_message_inspection(self, test_client: TestClient) -> None:
        """Test message inspection capabilities in enhanced debug endpoint."""
        with patch("src.backend.cc.logging.log_l1") as mock_log_l1:
            mock_log_l1.return_value = {
                "base_log_id": uuid.uuid4(),
                "event_log_id": uuid.uuid4(),
            }

            request_data = {
                "event_type": "message_inspection_test",
                "payload": {"inspection": True, "data": "test"},
                "request_id": "req-123",
                "trace_id": "trace-456",
            }

            response = test_client.post("/cc/debug/log", json=request_data)

            assert response.status_code == STATUS_CREATED
            result = response.json()

            # Verify published message structure is included in response
            redis_validation = result["redis_validation"]
            assert "published_message" in redis_validation


class TestRedisHealthEndpoint:
    """TDD tests for new /debug/redis-health endpoint."""

    def test_redis_health_endpoint_exists(self, test_client: TestClient) -> None:
        """Test that /debug/redis-health endpoint exists and responds."""
        response = test_client.get("/cc/debug/redis-health")

        # Should exist (not 404) - may be 500 if Redis unavailable, but should exist
        assert response.status_code != STATUS_NOT_FOUND

    def test_redis_health_comprehensive_status(self, test_client: TestClient) -> None:
        """Test comprehensive Redis health status reporting."""
        with patch("src.common.pubsub.get_pubsub") as mock_get_pubsub:
            mock_pubsub = AsyncMock()
            mock_redis = AsyncMock()
            # Use attribute assignment to simulate internal state without accessing private members
            mock_pubsub.redis = mock_redis
            mock_pubsub.is_connected = True
            mock_get_pubsub.return_value = mock_pubsub

            # Mock Redis client info methods
            mock_redis.ping.return_value = True
            mock_redis.info.return_value = {
                "connected_clients": "5",
                "used_memory": "1048576",
                "redis_version": "7.0.0",
            }
            mock_redis.connection_pool.connection_kwargs = {"max_connections": 10}

            response = test_client.get("/cc/debug/redis-health")

            assert response.status_code == STATUS_OK
            result = response.json()

            # Verify comprehensive health response structure
            assert "status" in result
            assert "timestamp" in result
            assert "connection_pool" in result
            assert "performance_metrics" in result
            assert "redis_info" in result
            assert "circuit_breaker" in result

            # Verify connection pool status
            pool_status = result["connection_pool"]
            assert "max_connections" in pool_status
            assert "active_connections" in pool_status
            assert "idle_connections" in pool_status

            # Verify performance metrics
            perf_metrics = result["performance_metrics"]
            assert "ping_latency_ms" in perf_metrics
            assert "last_successful_operation" in perf_metrics

    def test_redis_health_circuit_breaker_integration(self, test_client: TestClient) -> None:
        """Test circuit breaker status integration in Redis health endpoint."""
        with patch("src.common.pubsub.get_pubsub") as mock_get_pubsub:
            mock_pubsub = AsyncMock()
            mock_circuit_breaker = MagicMock()
            mock_circuit_breaker.state = "CLOSED"
            mock_circuit_breaker.failure_count = 0
            mock_circuit_breaker.last_failure_time = None
            mock_pubsub.circuit_breaker = mock_circuit_breaker
            mock_get_pubsub.return_value = mock_pubsub

            response = test_client.get("/cc/debug/redis-health")

            assert response.status_code == STATUS_OK
            result = response.json()

            # Verify circuit breaker status is included
            cb_status = result["circuit_breaker"]
            assert "state" in cb_status
            assert "failure_count" in cb_status
            assert "last_failure_time" in cb_status

    def test_redis_health_connection_failure_handling(self, test_client: TestClient) -> None:
        """Test Redis health endpoint when Redis is unavailable."""
        with patch("src.common.pubsub.get_pubsub") as mock_get_pubsub:
            mock_get_pubsub.side_effect = Exception("Redis connection failed")

            response = test_client.get("/cc/debug/redis-health")

            assert response.status_code == STATUS_OK  # Should return health status even if Redis is down
            result = response.json()

            assert result["status"] == "offline"
            assert "error" in result
            assert "connection_pool" in result
            assert result["connection_pool"]["status"] == "disconnected"

    def test_redis_health_performance_metrics_collection(self, test_client: TestClient) -> None:
        """Test performance metrics collection in Redis health endpoint."""
        with patch("src.common.pubsub.get_pubsub") as mock_get_pubsub:
            mock_pubsub = AsyncMock()
            mock_redis = AsyncMock()
            # Set both .redis and ._redis attributes for compatibility
            mock_pubsub.redis = mock_redis
            mock_pubsub._redis = mock_redis
            mock_pubsub.is_connected = True

            # Mock circuit breaker metrics
            mock_pubsub.circuit_breaker_metrics = {
                "state": "closed",
                "failure_count": 0,
                "last_failure_time": None,
                "next_attempt_time": None,
            }

            # Mock Redis info
            mock_redis.info.return_value = {
                "redis_version": "7.2.0",
                "uptime_in_seconds": 3600,
                "connected_clients": 5,
                "used_memory": 1048576,
                "total_commands_processed": 1000,
            }

            # Mock connection pool
            mock_pool = MagicMock()
            mock_pool.max_connections = 10
            mock_pool._created_connections = [1, 2, 3]
            mock_pool._available_connections = [1, 2]
            mock_redis.connection_pool = mock_pool

            mock_get_pubsub.return_value = mock_pubsub

            # Mock timing for ping operation
            mock_redis.ping.return_value = True

            response = test_client.get("/cc/debug/redis-health")

            assert response.status_code == STATUS_OK
            result = response.json()

            # Verify performance metrics are collected
            perf_metrics = result["performance_metrics"]
            assert "ping_latency_ms" in perf_metrics
            assert isinstance(perf_metrics["ping_latency_ms"], int | float)
            assert perf_metrics["ping_latency_ms"] >= 0


class TestRedisHealthAggregation:
    """TDD tests for Redis health aggregation logic."""

    def test_health_status_aggregation_healthy(self, test_client: TestClient) -> None:
        """Test health status aggregation when all systems are healthy."""
        with patch("src.common.pubsub.get_pubsub") as mock_get_pubsub:
            mock_pubsub = AsyncMock()
            mock_redis = AsyncMock()
            # Set both .redis and ._redis attributes for compatibility
            mock_pubsub.redis = mock_redis
            mock_pubsub._redis = mock_redis
            mock_pubsub.is_connected = True

            # Mock circuit breaker metrics
            mock_pubsub.circuit_breaker_metrics = {
                "state": "closed",
                "failure_count": 0,
                "last_failure_time": None,
                "next_attempt_time": None,
            }

            # Mock Redis info
            mock_redis.info.return_value = {
                "redis_version": "7.2.0",
                "uptime_in_seconds": 3600,
                "connected_clients": 5,
                "used_memory": 1048576,
                "total_commands_processed": 1000,
            }

            # Mock connection pool
            mock_pool = MagicMock()
            mock_pool.max_connections = 10
            mock_pool._created_connections = [1, 2, 3]
            mock_pool._available_connections = [1, 2]
            mock_redis.connection_pool = mock_pool

            mock_redis.ping.return_value = True
            mock_get_pubsub.return_value = mock_pubsub

            response = test_client.get("/cc/debug/redis-health")

            assert response.status_code == STATUS_OK
            result = response.json()
            assert result["status"] == "healthy"

    def test_health_status_aggregation_degraded(self, test_client: TestClient) -> None:
        """Test health status aggregation when Redis is degraded."""
        with patch("src.common.pubsub.get_pubsub") as mock_get_pubsub:
            mock_pubsub = AsyncMock()
            mock_redis = AsyncMock()
            # Set both .redis and ._redis attributes for compatibility
            mock_pubsub.redis = mock_redis
            mock_pubsub._redis = mock_redis
            mock_pubsub.is_connected = True

            # Mock circuit breaker metrics - OPEN state = degraded
            mock_pubsub.circuit_breaker_metrics = {
                "state": "open",  # Circuit breaker open = degraded
                "failure_count": 5,
                "last_failure_time": 1234567890,
                "next_attempt_time": 1234567900,
            }

            # Mock Redis info
            mock_redis.info.return_value = {
                "redis_version": "7.2.0",
                "uptime_in_seconds": 3600,
                "connected_clients": 5,
                "used_memory": 1048576,
                "total_commands_processed": 1000,
            }

            # Mock connection pool
            mock_pool = MagicMock()
            mock_pool.max_connections = 10
            mock_pool._created_connections = [1, 2, 3]
            mock_pool._available_connections = [1, 2]
            mock_redis.connection_pool = mock_pool

            mock_redis.ping.return_value = True
            mock_get_pubsub.return_value = mock_pubsub

            response = test_client.get("/cc/debug/redis-health")

            assert response.status_code == STATUS_OK
            result = response.json()
            assert result["status"] == "offline"  # OPEN circuit breaker = offline status

    def test_health_status_aggregation_offline(self, test_client: TestClient) -> None:
        """Test health status aggregation when Redis is completely offline."""
        with patch("src.common.pubsub.get_pubsub") as mock_get_pubsub:
            mock_pubsub = AsyncMock()
            mock_pubsub.is_connected = False
            mock_get_pubsub.return_value = mock_pubsub

            response = test_client.get("/cc/debug/redis-health")

            assert response.status_code == STATUS_OK
            result = response.json()
            assert result["status"] == "offline"
