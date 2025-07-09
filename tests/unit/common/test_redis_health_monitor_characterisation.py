"""Characterisation tests for redis_health_monitor.py missing coverage.

These tests capture the current behavior of uncovered lines before applying
Living Patterns. They focus on Docker exception paths and edge cases.

Pattern Applied: error_handling.py v2.1.0 (characterisation phase)
"""

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.redis_health_monitor import (
    RedisContainerState,
    RedisHealthMonitor,
    RedisHealthStatus,
    cleanup_redis_monitor,
    get_redis_health_monitor,
)


class TestRedisHealthMonitorCharacterisation:
    """Test uncovered lines in redis_health_monitor.py."""

    def test_docker_import_error_handling(self) -> None:
        """Test Docker import error handling (lines 27-31)."""
        # This tests the ImportError branch when docker is not available
        with patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", False):
            monitor = RedisHealthMonitor()
            # Should work without docker
            assert monitor.container_name == "cos_redis"
            assert monitor.auto_recovery is True

    async def test_start_monitoring_already_started(self) -> None:
        """Test start_monitoring when already started (lines 96-97)."""
        monitor = RedisHealthMonitor()
        monitor._monitoring = True  # Simulate already started

        with patch("src.common.redis_health_monitor.logger") as mock_logger:
            await monitor.start_monitoring()
            mock_logger.warning.assert_called_once_with("Redis health monitoring already started")

    async def test_stop_monitoring_not_started(self) -> None:
        """Test stop_monitoring when not started (line 106)."""
        monitor = RedisHealthMonitor()
        monitor._monitoring = False  # Ensure not started

        # Should return immediately without errors
        await monitor.stop_monitoring()
        assert monitor._monitoring is False

    async def test_stop_monitoring_docker_cleanup_error(self) -> None:
        """Test Docker client cleanup error handling (lines 118-123)."""
        monitor = RedisHealthMonitor()
        monitor._monitoring = True

        # Mock docker client that raises exception on close
        mock_docker_client = MagicMock()
        mock_docker_client.close.side_effect = Exception("Docker close error")
        monitor._docker_client = mock_docker_client

        with patch("src.common.redis_health_monitor.logger") as mock_logger:
            await monitor.stop_monitoring()
            mock_logger.exception.assert_called_once_with("Error closing Docker client")
            assert monitor._docker_client is None

    async def test_monitoring_loop_exception_handling(self) -> None:
        """Test monitoring loop exception handling (lines 127-152)."""
        monitor = RedisHealthMonitor()
        monitor._monitoring = True

        # Mock check_health to raise exception
        with (
            patch.object(monitor, "check_health", side_effect=Exception("Test error")),
            patch("src.common.redis_health_monitor.logger") as mock_logger,
            patch("asyncio.sleep") as mock_sleep,
        ):
            # Stop monitoring after first iteration
            def stop_monitoring(*args: Any) -> AsyncMock:
                monitor._monitoring = False
                return AsyncMock()

            mock_sleep.side_effect = stop_monitoring
            await monitor._monitoring_loop()

            mock_logger.exception.assert_called_once_with("Error in Redis health monitoring loop")

    async def test_monitoring_loop_cancelled_error(self) -> None:
        """Test monitoring loop CancelledError handling (lines 148-149)."""
        monitor = RedisHealthMonitor()
        monitor._monitoring = True

        with patch.object(monitor, "check_health", side_effect=asyncio.CancelledError):
            # CancelledError should cause the loop to break, not raise
            await monitor._monitoring_loop()
            # If we get here, the loop properly handled CancelledError
            assert True  # Loop should have exited properly

    async def test_monitoring_loop_health_status_logging(self) -> None:
        """Test health status logging in monitoring loop (lines 132-144)."""
        monitor = RedisHealthMonitor()
        monitor._monitoring = True

        # Test PAUSED state logging
        paused_status = RedisHealthStatus(container_state=RedisContainerState.PAUSED, auto_recovery_attempted=True)

        with (
            patch.object(monitor, "check_health", return_value=paused_status),
            patch("src.common.redis_health_monitor.logger") as mock_logger,
            patch("asyncio.sleep") as mock_sleep,
        ):

            def stop_monitoring(*args: Any) -> AsyncMock:
                monitor._monitoring = False
                return AsyncMock()

            mock_sleep.side_effect = stop_monitoring
            await monitor._monitoring_loop()

            mock_logger.warning.assert_called_once_with(
                "CRITICAL: Redis container is PAUSED - %s", "auto-recovery attempted"
            )

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", True)
    async def test_get_container_state_stopped(self) -> None:
        """Test container state detection for stopped containers (lines 219-220)."""
        monitor = RedisHealthMonitor()

        with patch("docker.from_env") as mock_docker:
            mock_container = MagicMock()
            mock_container.status = "stopped"
            mock_docker.return_value.containers.get.return_value = mock_container

            state = await monitor._get_container_state()
            assert state == RedisContainerState.STOPPED

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", True)
    async def test_get_container_state_unknown_status(self) -> None:
        """Test unknown container status handling (lines 222-223)."""
        monitor = RedisHealthMonitor()

        with patch("docker.from_env") as mock_docker:
            mock_container = MagicMock()
            mock_container.status = "unknown_status"
            mock_docker.return_value.containers.get.return_value = mock_container

            with patch("src.common.redis_health_monitor.logger") as mock_logger:
                state = await monitor._get_container_state()
                assert state == RedisContainerState.UNKNOWN
                mock_logger.warning.assert_called_once_with("Unknown container status: %s", "unknown_status")

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", True)
    async def test_get_container_state_docker_exception(self) -> None:
        """Test DockerException handling (lines 229-231)."""
        monitor = RedisHealthMonitor()

        with patch("docker.from_env") as mock_docker:
            from docker.errors import DockerException

            mock_docker.return_value.containers.get.side_effect = DockerException("Docker error")

            with patch("src.common.redis_health_monitor.logger") as mock_logger:
                state = await monitor._get_container_state()
                assert state == RedisContainerState.UNKNOWN
                mock_logger.exception.assert_called_once_with("Error accessing Docker for container state check")

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", True)
    async def test_get_container_state_unexpected_exception(self) -> None:
        """Test unexpected exception handling (lines 233-234)."""
        monitor = RedisHealthMonitor()

        with patch("docker.from_env") as mock_docker:
            mock_docker.return_value.containers.get.side_effect = RuntimeError("Unexpected error")

            with patch("src.common.redis_health_monitor.logger") as mock_logger:
                state = await monitor._get_container_state()
                assert state == RedisContainerState.UNKNOWN
                mock_logger.exception.assert_called_once_with("Unexpected error checking container state")

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", True)
    async def test_unpause_container_docker_exception(self) -> None:
        """Test unpause DockerException handling (lines 266-268)."""
        monitor = RedisHealthMonitor()

        with patch("docker.from_env") as mock_docker:
            from docker.errors import DockerException

            mock_docker.return_value.containers.get.side_effect = DockerException("Docker error")

            with patch("src.common.redis_health_monitor.logger") as mock_logger:
                result = await monitor._unpause_container()
                assert result is False
                mock_logger.exception.assert_called_once_with("Docker error during container unpause")

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", True)
    async def test_unpause_container_unexpected_exception(self) -> None:
        """Test unpause unexpected exception handling (lines 270-271)."""
        monitor = RedisHealthMonitor()

        with patch("docker.from_env") as mock_docker:
            mock_docker.return_value.containers.get.side_effect = RuntimeError("Unexpected error")

            with patch("src.common.redis_health_monitor.logger") as mock_logger:
                result = await monitor._unpause_container()
                assert result is False
                mock_logger.exception.assert_called_once_with("Unexpected error during container unpause")

    async def test_test_redis_connection_import_error(self) -> None:
        """Test Redis connection import error handling (lines 284-286)."""
        monitor = RedisHealthMonitor()

        # Mock the import to raise ImportError at the function level
        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "redis.asyncio":
                raise ImportError("Redis not available")
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            success, latency, error = await monitor._test_redis_connection()
            assert success is False
            assert latency is None
            assert error is not None and "Redis package not available" in error

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", False)
    async def test_detect_security_alerts_docker_unavailable(self) -> None:
        """Test security alerts when Docker unavailable (line 324)."""
        monitor = RedisHealthMonitor()

        alerts = await monitor.detect_security_alerts()
        assert alerts == []

    @patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", True)
    async def test_detect_security_alerts_exception(self) -> None:
        """Test security alerts exception handling (lines 352-353)."""
        monitor = RedisHealthMonitor()

        with patch("docker.from_env") as mock_docker:
            mock_docker.return_value.containers.get.side_effect = Exception("Docker error")

            with patch("src.common.redis_health_monitor.logger") as mock_logger:
                alerts = await monitor.detect_security_alerts()
                assert alerts == []
                mock_logger.exception.assert_called_once_with("Error checking Redis container logs for security alerts")

    async def test_cleanup_redis_monitor_with_monitor(self) -> None:
        """Test cleanup when monitor exists (lines 435-437)."""
        # Setup global monitor
        import src.common.redis_health_monitor as monitor_module

        mock_monitor = AsyncMock()
        monitor_module._health_monitor = mock_monitor

        await cleanup_redis_monitor()

        mock_monitor.stop_monitoring.assert_called_once()
        assert monitor_module._health_monitor is None


class TestRedisHealthMonitorPerformance:
    """Performance characterisation tests."""

    async def test_check_health_performance(self) -> None:
        """Test check_health performance baseline."""
        monitor = RedisHealthMonitor()

        # Mock all Docker operations to be fast
        with (
            patch("src.common.redis_health_monitor._DOCKER_AVAILABLE", True),
            patch("docker.from_env") as mock_docker,
            patch.object(monitor, "_test_redis_connection", return_value=(True, 0.5, None)),
        ):
            mock_container = MagicMock()
            mock_container.status = "running"
            mock_docker.return_value.containers.get.return_value = mock_container

            start_time = time.perf_counter()
            await monitor.check_health()
            elapsed = time.perf_counter() - start_time

            # Should complete in reasonable time
            assert elapsed < 0.1  # 100ms threshold


@pytest.mark.asyncio
class TestRedisHealthMonitorIntegration:
    """Integration tests for global functions."""

    async def test_get_redis_health_monitor_singleton(self) -> None:
        """Test singleton behavior."""
        monitor1 = await get_redis_health_monitor()
        monitor2 = await get_redis_health_monitor()

        assert monitor1 is monitor2
        assert isinstance(monitor1, RedisHealthMonitor)

    async def test_redis_health_status_initialization(self) -> None:
        """Test RedisHealthStatus initialization."""
        status = RedisHealthStatus()

        assert status.container_state == RedisContainerState.UNKNOWN
        assert status.connection_successful is False
        assert status.auto_recovery_attempted is False
        assert status.requires_manual_intervention is False
        assert isinstance(status.timestamp, float)
