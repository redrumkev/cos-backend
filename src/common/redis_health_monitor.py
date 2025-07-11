"""Redis Health Monitor with Auto-Recovery.

This module provides Redis health monitoring and auto-recovery mechanisms to prevent
manual intervention requirements in production. Addresses the critical issue where
Redis gets paused during circuit breaker tests and requires manual unpause.

Pattern Applied: error_handling.py v2.1.0, async_handler.py v2.1.0
Version: 2025-07-08 v2.1.0 (Living Patterns Enhancement)
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Pattern v2.1.0: Enhanced error handling with structured categories
from ..core_v2.patterns.error_handling import COSError, ErrorCategory, error_handler, map_redis_error

logger = logging.getLogger(__name__)

# Import Docker client with graceful degradation
try:
    import docker
    from docker.errors import DockerException

    _DOCKER_AVAILABLE = True
except ImportError:
    logger.warning("Docker package not available. Container management will be disabled.")
    _DOCKER_AVAILABLE = False
    docker = None
    DockerException = Exception


class RedisContainerState(Enum):
    """Redis container states."""

    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    UNKNOWN = "unknown"
    NOT_FOUND = "not_found"


@dataclass
class RedisHealthStatus:
    """Redis health status with detailed diagnostics."""

    timestamp: float = field(default_factory=time.time)
    container_state: RedisContainerState = RedisContainerState.UNKNOWN
    container_name: str | None = None
    connection_successful: bool = False
    ping_latency_ms: float | None = None
    error_message: str | None = None
    auto_recovery_attempted: bool = False
    auto_recovery_successful: bool = False
    requires_manual_intervention: bool = False


class RedisHealthMonitor:
    """Redis health monitor with auto-recovery capabilities.

    Features:
    - Container state detection (running/paused/stopped)
    - Auto-unpause when Redis container is paused
    - Connection health checks with latency monitoring
    - Security alert pattern detection
    - Production-safe auto-recovery
    """

    def __init__(
        self,
        container_name: str = "cos_redis",
        check_interval: float = 10.0,
        auto_recovery: bool = True,
    ) -> None:
        """Initialize Redis health monitor.

        Args:
        ----
            container_name: Name of Redis Docker container
            check_interval: Health check interval in seconds
            auto_recovery: Enable automatic recovery actions

        """
        self.container_name = container_name
        self.check_interval = check_interval
        self.auto_recovery = auto_recovery
        self._monitoring = False
        self._monitor_task: asyncio.Task[None] | None = None
        self._docker_client: Any = None
        self._redis_client: Any = None

    async def start_monitoring(self) -> None:
        """Start continuous Redis health monitoring."""
        if self._monitoring:
            logger.warning("Redis health monitoring already started")
            return

        logger.info("Starting Redis health monitoring (container: %s)", self.container_name)
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self) -> None:
        """Stop Redis health monitoring."""
        if not self._monitoring:
            return

        logger.info("Stopping Redis health monitoring")
        self._monitoring = False

        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task

        # Cleanup Docker client
        if self._docker_client:
            try:
                self._docker_client.close()
            except Exception:
                logger.exception("Error closing Docker client")
            finally:
                self._docker_client = None

    async def _monitoring_loop(self) -> None:
        """Run main monitoring loop."""
        while self._monitoring:
            try:
                health_status = await self.check_health()

                # Log health status
                if health_status.container_state == RedisContainerState.PAUSED:
                    recovery_status = (
                        "auto-recovery attempted"
                        if health_status.auto_recovery_attempted
                        else "manual intervention required"
                    )
                    logger.warning("CRITICAL: Redis container is PAUSED - %s", recovery_status)
                elif health_status.container_state == RedisContainerState.STOPPED:
                    logger.error("CRITICAL: Redis container is STOPPED - requires manual intervention")
                elif not health_status.connection_successful:
                    logger.warning("Redis connection failed: %s", health_status.error_message)
                else:
                    logger.debug("Redis health check passed (ping: %.2fms)", health_status.ping_latency_ms or 0)

                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in Redis health monitoring loop")
                await asyncio.sleep(self.check_interval)

    async def check_health(self) -> RedisHealthStatus:
        """Perform comprehensive Redis health check with auto-recovery.

        Returns
        -------
            RedisHealthStatus with detailed diagnostics and recovery actions

        """
        health_status = RedisHealthStatus(container_name=self.container_name)

        # Step 1: Check container state
        container_state = await self._get_container_state()
        health_status.container_state = container_state

        # Step 2: Auto-recovery for paused container
        if container_state == RedisContainerState.PAUSED and self.auto_recovery:
            logger.warning("Redis container is PAUSED - attempting auto-recovery")
            health_status.auto_recovery_attempted = True
            unpause_success = await self._unpause_container()
            health_status.auto_recovery_successful = unpause_success

            if unpause_success:
                logger.info("Redis container successfully unpaused")
                # Re-check container state after unpause
                container_state = await self._get_container_state()
                health_status.container_state = container_state
            else:
                logger.error("Failed to unpause Redis container - manual intervention required")
                health_status.requires_manual_intervention = True
                return health_status

        # Step 3: Test Redis connection if container is running
        if container_state == RedisContainerState.RUNNING:
            ping_success, ping_latency, error_msg = await self._test_redis_connection()
            health_status.connection_successful = ping_success
            health_status.ping_latency_ms = ping_latency
            health_status.error_message = error_msg
        else:
            health_status.connection_successful = False
            health_status.error_message = f"Container not running: {container_state.value}"

        # Step 4: Set manual intervention flag for unrecoverable states
        if container_state in (RedisContainerState.STOPPED, RedisContainerState.NOT_FOUND):
            health_status.requires_manual_intervention = True

        return health_status

    async def _get_container_state(self) -> RedisContainerState:
        """Get Redis container state using Docker API.

        Pattern Applied: error_handling.py v2.1.0 (Structured error handling)
        """
        if not _DOCKER_AVAILABLE:
            logger.debug("Docker not available - skipping container state check")
            return RedisContainerState.UNKNOWN

        async with error_handler("get_container_state", logger, reraise=False):
            try:
                # Initialize Docker client if needed
                if not self._docker_client:
                    self._docker_client = docker.from_env()

                container = self._docker_client.containers.get(self.container_name)
                status = container.status.lower()

                if status == "running":
                    return RedisContainerState.RUNNING
                elif status == "paused":
                    return RedisContainerState.PAUSED
                elif status in ("stopped", "exited"):
                    return RedisContainerState.STOPPED
                else:
                    logger.warning("Unknown container status: %s", status)
                    return RedisContainerState.UNKNOWN

            except Exception as e:
                # Pattern v2.1.0: Structured error handling with appropriate categories
                if docker and isinstance(e, docker.errors.NotFound):
                    logger.warning("Redis container '%s' not found", self.container_name)
                    return RedisContainerState.NOT_FOUND
                elif isinstance(e, DockerException):
                    logger.exception("Error accessing Docker for container state check")
                    return RedisContainerState.UNKNOWN
                else:
                    logger.exception("Unexpected error checking container state")
                    return RedisContainerState.UNKNOWN

    async def _unpause_container(self) -> bool:
        """Unpause Redis container.

        Returns
        -------
            True if unpause was successful, False otherwise

        Pattern Applied: error_handling.py v2.1.0 (Structured error handling)

        """
        if not _DOCKER_AVAILABLE:
            logger.error("Docker not available - cannot unpause container")
            return False

        async with error_handler("unpause_container", logger, reraise=False):
            try:
                if not self._docker_client:
                    self._docker_client = docker.from_env()

                container = self._docker_client.containers.get(self.container_name)
                container.unpause()

                # Wait a moment for unpause to take effect
                await asyncio.sleep(1.0)

                # Verify unpause was successful
                container.reload()
                return bool(container.status.lower() == "running")

            except Exception as e:
                # Pattern v2.1.0: Structured error handling with appropriate categories
                if docker and isinstance(e, docker.errors.NotFound):
                    logger.error("Redis container '%s' not found for unpause", self.container_name)
                    return False
                elif isinstance(e, DockerException):
                    logger.exception("Docker error during container unpause")
                    return False
                else:
                    logger.exception("Unexpected error during container unpause")
                    return False

    async def _test_redis_connection(self) -> tuple[bool, float | None, str | None]:
        """Test Redis connection with ping.

        Returns
        -------
            Tuple of (success, latency_ms, error_message)

        Pattern Applied: error_handling.py v2.1.0 (Redis error mapping)

        """
        async with error_handler("redis_connection_test", logger, reraise=False):
            try:
                # Import Redis client lazily
                try:
                    import redis.asyncio as redis
                except ImportError:
                    return False, None, "Redis package not available"

                try:
                    from .redis_config import get_redis_config
                except ImportError:
                    return False, None, "Redis config not available"

                # Create Redis client if needed
                if not self._redis_client:
                    config = get_redis_config()
                    self._redis_client = redis.Redis.from_url(
                        config.redis_url,
                        decode_responses=False,
                        socket_connect_timeout=5,
                        socket_timeout=5,
                    )

                # Perform ping with timing
                start_time = time.perf_counter()
                await self._redis_client.ping()
                latency_ms = (time.perf_counter() - start_time) * 1000

                return True, latency_ms, None

            except Exception as e:
                # Pattern v2.1.0: Use Redis error mapping for structured error handling
                cos_error = map_redis_error(e)
                error_msg = f"Redis ping failed: {cos_error!s}"
                logger.debug(error_msg, extra={"error_category": cos_error.category.value})
                return False, None, error_msg

        # If error_handler swallows an exception, return failure
        return False, None, "Unexpected error in Redis connection test"

    async def detect_security_alerts(self) -> list[str]:
        """Detect Redis security alerts in container logs.

        Returns
        -------
            List of security alert messages found in logs

        Pattern Applied: error_handling.py v2.1.0 (Structured error handling)

        """
        if not _DOCKER_AVAILABLE:
            return []

        security_alerts = []

        async with error_handler("detect_security_alerts", logger, reraise=False):
            try:
                if not self._docker_client:
                    self._docker_client = docker.from_env()

                container = self._docker_client.containers.get(self.container_name)

                # Get recent logs
                logs = container.logs(tail=50, timestamps=True).decode("utf-8", errors="ignore")

                # Look for security alert patterns (using regex for flexible matching)
                security_patterns = [
                    r"Possible SECURITY ATTACK detected",
                    r"POST or Host: commands to Redis",
                    r"Cross Protocol Scripting",
                    r"Connection.*aborted",
                    r"SIGTERM scheduling shutdown",
                ]

                for line in logs.split("\n"):
                    for pattern in security_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            security_alerts.append(line.strip())
                            break  # Avoid duplicate matches for same line

            except Exception:
                # Pattern v2.1.0: Structured error handling with context
                logger.exception("Error checking Redis container logs for security alerts")

        return security_alerts

    async def ensure_redis_available(self) -> bool:
        """Ensure Redis is available for testing.

        This method performs a comprehensive check and auto-recovery to ensure
        Redis is ready for test execution. It's designed to be called before
        running tests that require Redis.

        Returns
        -------
            True if Redis is available and ready, False if manual intervention required

        Pattern Applied: error_handling.py v2.1.0 (Structured error handling)

        """
        async with error_handler("ensure_redis_available", logger, reraise=False):
            logger.info("Ensuring Redis availability for testing")

            health_status = await self.check_health()

            if health_status.connection_successful:
                logger.info("Redis is available and healthy")
                return True

            if health_status.requires_manual_intervention:
                logger.error("Redis requires manual intervention (state: %s)", health_status.container_state.value)
                return False

            if health_status.auto_recovery_attempted and not health_status.auto_recovery_successful:
                logger.error("Redis auto-recovery failed - manual intervention required")
                return False

            # If we got here, there might be a transient issue - retry once
            logger.info("Retrying Redis health check after initial failure")
            await asyncio.sleep(2.0)
            retry_status = await self.check_health()

            if retry_status.connection_successful:
                logger.info("Redis available after retry")
                return True

            logger.error("Redis still unavailable after retry - manual intervention may be required")
            return False


# Global singleton instance
_health_monitor: RedisHealthMonitor | None = None


async def get_redis_health_monitor() -> RedisHealthMonitor:
    """Get singleton Redis health monitor instance.

    Returns
    -------
        Configured RedisHealthMonitor instance

    Pattern Applied: error_handling.py v2.1.0 (Structured error handling)

    """
    global _health_monitor
    if _health_monitor is None:
        try:
            _health_monitor = RedisHealthMonitor()
        except Exception as e:
            logger.error("Failed to create Redis health monitor instance", exc_info=True)
            # Re-raise to maintain function contract - must return RedisHealthMonitor or fail
            raise COSError(
                message=f"Failed to create Redis health monitor: {e}",
                category=ErrorCategory.INTERNAL,
                details={"original_error": type(e).__name__},
            ) from e
    return _health_monitor


async def ensure_redis_available_for_tests() -> bool:
    """Ensure Redis is available for test execution.

    This is a convenience function that can be called before running tests
    to ensure Redis is in a good state and auto-recover from common issues
    like container pausing.

    Returns
    -------
        True if Redis is available, False if manual intervention required

    Pattern Applied: error_handling.py v2.1.0 (Structured error handling)

    """
    try:
        monitor = await get_redis_health_monitor()
        return await monitor.ensure_redis_available()
    except Exception:
        logger.error("Failed to ensure Redis availability for tests", exc_info=True)
        # Return False to indicate Redis is not available, don't raise
        return False


async def cleanup_redis_monitor() -> None:
    """Clean up Redis health monitor singleton.

    Pattern Applied: error_handling.py v2.1.0 (Structured error handling)
    """
    global _health_monitor
    if _health_monitor:
        try:
            await _health_monitor.stop_monitoring()
        except Exception:
            # Log error but continue with cleanup
            logger.exception("Error during Redis health monitor cleanup")
        finally:
            _health_monitor = None
