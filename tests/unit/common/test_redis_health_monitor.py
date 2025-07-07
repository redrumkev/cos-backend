"""Tests for Redis Health Monitor with auto-recovery functionality.

This module tests the Redis health monitoring and auto-recovery mechanisms
designed to prevent manual intervention requirements in production.
"""

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.common.redis_health_monitor import (
    RedisContainerState,
    RedisHealthMonitor,
    RedisHealthStatus,
    ensure_redis_available_for_tests,
    get_redis_health_monitor,
)


class TestRedisHealthMonitor:
    """Test cases for Redis health monitoring functionality."""

    @pytest.fixture
    def health_monitor(self) -> RedisHealthMonitor:
        """Create a Redis health monitor instance for testing."""
        return RedisHealthMonitor(
            container_name="test_redis",
            check_interval=0.1,  # Fast for testing
            auto_recovery=True,
        )

    async def test_initial_state(self, health_monitor: RedisHealthMonitor) -> None:
        """Test health monitor initial state."""
        assert health_monitor.container_name == "test_redis"
        assert health_monitor.check_interval == 0.1
        assert health_monitor.auto_recovery is True
        assert health_monitor._monitoring is False
        assert health_monitor._monitor_task is None

    async def test_start_stop_monitoring(self, health_monitor: RedisHealthMonitor) -> None:
        """Test starting and stopping monitoring."""
        # Start monitoring
        await health_monitor.start_monitoring()
        assert health_monitor._monitoring is True
        assert health_monitor._monitor_task is not None

        # Stop monitoring
        await health_monitor.stop_monitoring()
        assert health_monitor._monitoring is False

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", True)
    @patch("src.common.redis_health_monitor.docker")
    async def test_get_container_state_running(self, mock_docker: Mock, health_monitor: RedisHealthMonitor) -> None:
        """Test getting container state when running."""
        # Mock Docker client and container
        mock_client = Mock()
        mock_container = Mock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client

        state = await health_monitor._get_container_state()
        assert state == RedisContainerState.RUNNING

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", True)
    @patch("src.common.redis_health_monitor.docker")
    async def test_get_container_state_paused(self, mock_docker: Mock, health_monitor: RedisHealthMonitor) -> None:
        """Test getting container state when paused."""
        # Mock Docker client and container
        mock_client = Mock()
        mock_container = Mock()
        mock_container.status = "paused"
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client

        state = await health_monitor._get_container_state()
        assert state == RedisContainerState.PAUSED

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", True)
    @patch("src.common.redis_health_monitor.docker")
    async def test_get_container_state_not_found(self, mock_docker: Mock, health_monitor: RedisHealthMonitor) -> None:
        """Test getting container state when container not found."""
        # Mock Docker client to raise NotFound
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_docker.errors.NotFound = Exception
        mock_client.containers.get.side_effect = mock_docker.errors.NotFound

        state = await health_monitor._get_container_state()
        assert state == RedisContainerState.NOT_FOUND

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", False)
    async def test_get_container_state_docker_unavailable(self, health_monitor: RedisHealthMonitor) -> None:
        """Test getting container state when Docker is unavailable."""
        state = await health_monitor._get_container_state()
        assert state == RedisContainerState.UNKNOWN

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", True)
    @patch("src.common.redis_health_monitor.docker")
    async def test_unpause_container_success(self, mock_docker: Mock, health_monitor: RedisHealthMonitor) -> None:
        """Test successful container unpause."""
        # Mock Docker client and container
        mock_client = Mock()
        mock_container = Mock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client

        success = await health_monitor._unpause_container()
        assert success is True
        mock_container.unpause.assert_called_once()
        mock_container.reload.assert_called_once()

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", True)
    @patch("src.common.redis_health_monitor.docker")
    async def test_unpause_container_not_found(self, mock_docker: Mock, health_monitor: RedisHealthMonitor) -> None:
        """Test container unpause when container not found."""
        # Mock Docker client to raise NotFound
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_docker.errors.NotFound = Exception
        mock_client.containers.get.side_effect = mock_docker.errors.NotFound

        success = await health_monitor._unpause_container()
        assert success is False

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", False)
    async def test_unpause_container_docker_unavailable(self, health_monitor: RedisHealthMonitor) -> None:
        """Test container unpause when Docker is unavailable."""
        success = await health_monitor._unpause_container()
        assert success is False

    async def test_test_redis_connection_success(self, health_monitor: RedisHealthMonitor) -> None:
        """Test successful Redis connection."""
        # Mock Redis client
        mock_client = AsyncMock()

        # Mock the config
        mock_config = Mock()
        mock_config.redis_url = "redis://localhost:6379"

        # Patch the exact import path used in the function
        with (
            patch("redis.asyncio.Redis") as mock_redis_class,
            patch("src.common.redis_config.get_redis_config", return_value=mock_config),
        ):
            mock_redis_class.from_url.return_value = mock_client

            success, latency, error = await health_monitor._test_redis_connection()

            assert success is True
            assert latency is not None
            assert latency > 0
            assert error is None
            mock_client.ping.assert_called_once()
            mock_redis_class.from_url.assert_called_once_with(
                "redis://localhost:6379",
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
            )

    async def test_test_redis_connection_import_error(self, health_monitor: RedisHealthMonitor) -> None:
        """Test Redis connection when Redis package not available."""

        # Simulate ImportError when trying to import redis.asyncio
        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "redis.asyncio":
                raise ImportError("No module named 'redis'")
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            success, latency, error = await health_monitor._test_redis_connection()

            assert success is False
            assert latency is None
            assert "Redis package not available" in str(error)

    async def test_test_redis_connection_failure(self, health_monitor: RedisHealthMonitor) -> None:
        """Test Redis connection failure."""
        # Mock Redis client
        mock_client = AsyncMock()
        mock_client.ping.side_effect = Exception("Connection failed")

        # Mock the config
        mock_config = Mock()
        mock_config.redis_url = "redis://localhost:6379"

        # Patch the exact import path used in the function
        with (
            patch("redis.asyncio.Redis") as mock_redis_class,
            patch("src.common.redis_config.get_redis_config", return_value=mock_config),
        ):
            mock_redis_class.from_url.return_value = mock_client

            success, latency, error = await health_monitor._test_redis_connection()

            assert success is False
            assert latency is None
            assert error is not None and "Connection failed" in error

    async def test_check_health_running_and_connected(self, health_monitor: RedisHealthMonitor) -> None:
        """Test health check when container is running and Redis is connected."""
        with (
            patch.object(health_monitor, "_get_container_state", return_value=RedisContainerState.RUNNING),
            patch.object(health_monitor, "_test_redis_connection", return_value=(True, 1.5, None)),
        ):
            health_status = await health_monitor.check_health()

            assert health_status.container_state == RedisContainerState.RUNNING
            assert health_status.connection_successful is True
            assert health_status.ping_latency_ms == 1.5
            assert health_status.error_message is None
            assert health_status.auto_recovery_attempted is False
            assert health_status.requires_manual_intervention is False

    async def test_check_health_paused_with_auto_recovery(self, health_monitor: RedisHealthMonitor) -> None:
        """Test health check when container is paused and auto-recovery succeeds."""
        with (
            patch.object(
                health_monitor,
                "_get_container_state",
                side_effect=[
                    RedisContainerState.PAUSED,
                    RedisContainerState.RUNNING,
                ],
            ),
            patch.object(health_monitor, "_unpause_container", return_value=True),
            patch.object(health_monitor, "_test_redis_connection", return_value=(True, 2.0, None)),
        ):
            health_status = await health_monitor.check_health()

            assert health_status.container_state == RedisContainerState.RUNNING
            assert health_status.connection_successful is True
            assert health_status.auto_recovery_attempted is True
            assert health_status.auto_recovery_successful is True
            assert health_status.requires_manual_intervention is False

    async def test_check_health_paused_recovery_fails(self, health_monitor: RedisHealthMonitor) -> None:
        """Test health check when container is paused and auto-recovery fails."""
        with (
            patch.object(health_monitor, "_get_container_state", return_value=RedisContainerState.PAUSED),
            patch.object(health_monitor, "_unpause_container", return_value=False),
        ):
            health_status = await health_monitor.check_health()

            assert health_status.container_state == RedisContainerState.PAUSED
            assert health_status.connection_successful is False
            assert health_status.auto_recovery_attempted is True
            assert health_status.auto_recovery_successful is False
            assert health_status.requires_manual_intervention is True

    async def test_check_health_stopped_container(self, health_monitor: RedisHealthMonitor) -> None:
        """Test health check when container is stopped."""
        with patch.object(health_monitor, "_get_container_state", return_value=RedisContainerState.STOPPED):
            health_status = await health_monitor.check_health()

            assert health_status.container_state == RedisContainerState.STOPPED
            assert health_status.connection_successful is False
            assert health_status.auto_recovery_attempted is False
            assert health_status.requires_manual_intervention is True

    async def test_ensure_redis_available_success(self, health_monitor: RedisHealthMonitor) -> None:
        """Test ensuring Redis availability when it's healthy."""
        mock_health_status = RedisHealthStatus(
            container_state=RedisContainerState.RUNNING,
            connection_successful=True,
        )

        with patch.object(health_monitor, "check_health", return_value=mock_health_status):
            available = await health_monitor.ensure_redis_available()
            assert available is True

    async def test_ensure_redis_available_manual_intervention(self, health_monitor: RedisHealthMonitor) -> None:
        """Test ensuring Redis availability when manual intervention is required."""
        mock_health_status = RedisHealthStatus(
            container_state=RedisContainerState.STOPPED,
            connection_successful=False,
            requires_manual_intervention=True,
        )

        with patch.object(health_monitor, "check_health", return_value=mock_health_status):
            available = await health_monitor.ensure_redis_available()
            assert available is False

    async def test_ensure_redis_available_recovery_fails(self, health_monitor: RedisHealthMonitor) -> None:
        """Test ensuring Redis availability when auto-recovery fails."""
        mock_health_status = RedisHealthStatus(
            container_state=RedisContainerState.PAUSED,
            connection_successful=False,
            auto_recovery_attempted=True,
            auto_recovery_successful=False,
        )

        with patch.object(health_monitor, "check_health", return_value=mock_health_status):
            available = await health_monitor.ensure_redis_available()
            assert available is False

    async def test_ensure_redis_available_retry_success(self, health_monitor: RedisHealthMonitor) -> None:
        """Test ensuring Redis availability with retry success."""
        # First check fails, retry succeeds
        mock_health_status_1 = RedisHealthStatus(
            container_state=RedisContainerState.RUNNING,
            connection_successful=False,
            error_message="Temporary connection error",
        )
        mock_health_status_2 = RedisHealthStatus(
            container_state=RedisContainerState.RUNNING,
            connection_successful=True,
        )

        with patch.object(health_monitor, "check_health", side_effect=[mock_health_status_1, mock_health_status_2]):
            available = await health_monitor.ensure_redis_available()
            assert available is True

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", True)
    @patch("src.common.redis_health_monitor.docker")
    async def test_detect_security_alerts(self, mock_docker: Mock, health_monitor: RedisHealthMonitor) -> None:
        """Test detecting security alerts in Redis logs."""
        # Mock Docker client and container logs
        mock_client = Mock()
        mock_container = Mock()
        mock_logs = (
            "2025-07-02 00:31:55.000 [INFO] Starting Redis\n"
            "2025-07-02 00:31:56.000 [WARNING] Possible SECURITY ATTACK detected\n"
            "2025-07-02 00:31:57.000 [ERROR] Connection from 172.18.0.1:56516 aborted\n"
            "2025-07-02 00:31:58.000 [INFO] Ready to accept connections\n"
        )
        mock_container.logs.return_value = mock_logs.encode()
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client

        alerts = await health_monitor.detect_security_alerts()

        assert len(alerts) == 2
        assert any("SECURITY ATTACK" in alert for alert in alerts)
        assert any("aborted" in alert for alert in alerts)

    async def test_auto_recovery_disabled(self) -> None:
        """Test health monitor with auto-recovery disabled."""
        health_monitor = RedisHealthMonitor(auto_recovery=False)

        with (
            patch.object(health_monitor, "_get_container_state", return_value=RedisContainerState.PAUSED),
            patch.object(health_monitor, "_unpause_container") as mock_unpause,
        ):
            health_status = await health_monitor.check_health()

            assert health_status.container_state == RedisContainerState.PAUSED
            assert health_status.auto_recovery_attempted is False
            mock_unpause.assert_not_called()


class TestGlobalFunctions:
    """Test cases for global helper functions."""

    async def test_get_redis_health_monitor_singleton(self) -> None:
        """Test that get_redis_health_monitor returns the same instance."""
        monitor1 = await get_redis_health_monitor()
        monitor2 = await get_redis_health_monitor()
        assert monitor1 is monitor2

    async def test_ensure_redis_available_for_tests(self) -> None:
        """Test the convenience function for test Redis availability."""
        with patch("src.common.redis_health_monitor.get_redis_health_monitor") as mock_get_monitor:
            mock_monitor = AsyncMock()
            mock_monitor.ensure_redis_available.return_value = True
            mock_get_monitor.return_value = mock_monitor

            available = await ensure_redis_available_for_tests()
            assert available is True
            mock_monitor.ensure_redis_available.assert_called_once()


class TestRedisHealthStatus:
    """Test cases for RedisHealthStatus dataclass."""

    def test_redis_health_status_defaults(self) -> None:
        """Test default values of RedisHealthStatus."""
        status = RedisHealthStatus()

        assert status.container_state == RedisContainerState.UNKNOWN
        assert status.container_name is None
        assert status.connection_successful is False
        assert status.ping_latency_ms is None
        assert status.error_message is None
        assert status.auto_recovery_attempted is False
        assert status.auto_recovery_successful is False
        assert status.requires_manual_intervention is False
        assert isinstance(status.timestamp, float)

    def test_redis_health_status_custom_values(self) -> None:
        """Test RedisHealthStatus with custom values."""
        status = RedisHealthStatus(
            container_state=RedisContainerState.RUNNING,
            container_name="test_redis",
            connection_successful=True,
            ping_latency_ms=1.5,
            auto_recovery_attempted=True,
            auto_recovery_successful=True,
        )

        assert status.container_state == RedisContainerState.RUNNING
        assert status.container_name == "test_redis"
        assert status.connection_successful is True
        assert status.ping_latency_ms == 1.5
        assert status.auto_recovery_attempted is True
        assert status.auto_recovery_successful is True
        assert status.requires_manual_intervention is False
