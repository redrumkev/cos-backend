"""Docker container utilities for robust test infrastructure.

This module provides Docker container management with auto-recovery, retry logic,
and state verification to eliminate manual intervention requirements.
"""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# Import Docker with graceful degradation
try:
    import docker
    from docker.errors import DockerException, NotFound

    _DOCKER_AVAILABLE = True
except ImportError:
    logger.warning("Docker package not available. Container management will be disabled.")
    _DOCKER_AVAILABLE = False
    docker = None
    DockerException = Exception
    NotFound = Exception


class ContainerState(Enum):
    """Docker container states."""

    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    RESTARTING = "restarting"
    UNKNOWN = "unknown"
    NOT_FOUND = "not_found"


# Global container locks to prevent concurrent modifications
_container_locks: dict[str, asyncio.Lock] = {}


def get_container_lock(container_name: str) -> asyncio.Lock:
    """Get or create a lock for a specific container."""
    if container_name not in _container_locks:
        _container_locks[container_name] = asyncio.Lock()
    return _container_locks[container_name]


class DockerHealthManager:
    """Docker container health manager with auto-recovery capabilities.

    Features:
    - Container state detection and verification
    - Exponential backoff retry logic
    - State transition verification
    - Concurrent operation protection
    - Comprehensive error handling
    """

    def __init__(
        self,
        container_name: str,
        command_timeout: float = 60.0,
        max_retries: int = 5,
    ) -> None:
        """Initialize Docker health manager.

        Args:
        ----
            container_name: Name of Docker container to manage
            command_timeout: Timeout for Docker commands in seconds
            max_retries: Maximum number of retry attempts

        """
        self.container_name = container_name
        self.command_timeout = command_timeout
        self.max_retries = max_retries
        self._docker_client: Any = None

    def _get_docker_client(self) -> Any:
        """Get or create Docker client."""
        if not _DOCKER_AVAILABLE:
            raise RuntimeError("Docker package not available")

        if not self._docker_client:
            self._docker_client = docker.from_env()
        return self._docker_client

    async def get_container_state(self) -> ContainerState:
        """Get current container state with error handling."""
        if not _DOCKER_AVAILABLE:
            logger.debug("Docker not available - skipping container state check")
            return ContainerState.UNKNOWN

        try:
            client = self._get_docker_client()
            container = await asyncio.to_thread(client.containers.get, self.container_name)
            status = container.status.lower()

            if status == "running":
                return ContainerState.RUNNING
            elif status == "paused":
                return ContainerState.PAUSED
            elif status in ("stopped", "exited"):
                return ContainerState.STOPPED
            elif status == "restarting":
                return ContainerState.RESTARTING
            else:
                logger.warning(f"Unknown container status '{status}' for {self.container_name}")
                return ContainerState.UNKNOWN

        except NotFound:
            logger.warning(f"Container '{self.container_name}' not found")
            return ContainerState.NOT_FOUND
        except Exception as e:
            logger.exception(f"Error checking container state for {self.container_name}: {e}")
            return ContainerState.UNKNOWN

    async def wait_for_state(
        self, desired_state: ContainerState, timeout: float = 10.0, poll_interval: float = 0.5
    ) -> bool:
        """Wait for container to reach desired state.

        Args:
        ----
            desired_state: Target container state
            timeout: Maximum time to wait in seconds
            poll_interval: Time between state checks in seconds

        Returns:
        -------
            True if desired state reached, False on timeout

        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            current_state = await self.get_container_state()
            if current_state == desired_state:
                return True

            # Handle special cases
            if current_state == ContainerState.NOT_FOUND:
                logger.error(f"Container {self.container_name} not found while waiting for {desired_state.value}")
                return False

            await asyncio.sleep(poll_interval)

        logger.warning(
            f"Timeout waiting for {self.container_name} to reach {desired_state.value} state "
            f"(current: {(await self.get_container_state()).value})"
        )
        return False

    async def pause_container(self) -> bool:
        """Pause container with retry logic and state verification.

        Returns
        -------
            True if successfully paused, False otherwise

        """
        lock = get_container_lock(self.container_name)

        async with lock:
            # Check if already paused
            current_state = await self.get_container_state()
            if current_state == ContainerState.PAUSED:
                logger.info(f"Container {self.container_name} already paused")
                return True

            if current_state != ContainerState.RUNNING:
                logger.warning(f"Cannot pause container {self.container_name} in state {current_state.value}")
                return False

            # Retry with exponential backoff
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"Pausing container {self.container_name} (attempt {attempt + 1})")

                    client = self._get_docker_client()
                    container = await asyncio.to_thread(client.containers.get, self.container_name)
                    await asyncio.to_thread(container.pause)

                    # Wait for state transition
                    await asyncio.sleep(1.0)

                    # Verify paused state
                    if await self.wait_for_state(ContainerState.PAUSED, timeout=5.0):
                        logger.info(f"Successfully paused container {self.container_name}")
                        return True

                except Exception as e:
                    logger.warning(
                        f"Failed to pause {self.container_name} (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )

                    if attempt < self.max_retries - 1:
                        wait_time = min(2**attempt, 16)  # Max 16 seconds
                        logger.info(f"Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)

            logger.error(f"Failed to pause container {self.container_name} after {self.max_retries} attempts")
            return False

    async def unpause_container(self) -> bool:
        """Unpause container with retry logic and state verification.

        Returns
        -------
            True if successfully unpaused, False otherwise

        """
        lock = get_container_lock(self.container_name)

        async with lock:
            # Check current state
            current_state = await self.get_container_state()
            if current_state == ContainerState.RUNNING:
                logger.info(f"Container {self.container_name} already running")
                return True

            if current_state != ContainerState.PAUSED:
                logger.warning(f"Cannot unpause container {self.container_name} in state {current_state.value}")
                return False

            # Retry with exponential backoff
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"Unpausing container {self.container_name} (attempt {attempt + 1})")

                    client = self._get_docker_client()
                    container = await asyncio.to_thread(client.containers.get, self.container_name)
                    await asyncio.to_thread(container.unpause)

                    # Wait for state transition
                    await asyncio.sleep(1.0)

                    # Verify running state
                    if await self.wait_for_state(ContainerState.RUNNING, timeout=5.0):
                        logger.info(f"Successfully unpaused container {self.container_name}")
                        return True

                except Exception as e:
                    logger.warning(
                        f"Failed to unpause {self.container_name} (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )

                    if attempt < self.max_retries - 1:
                        wait_time = min(2**attempt, 16)  # Max 16 seconds
                        logger.info(f"Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)

            logger.error(f"Failed to unpause container {self.container_name} after {self.max_retries} attempts")
            return False

    async def stop_container(self) -> bool:
        """Stop container with retry logic."""
        lock = get_container_lock(self.container_name)

        async with lock:
            current_state = await self.get_container_state()
            if current_state == ContainerState.STOPPED:
                logger.info(f"Container {self.container_name} already stopped")
                return True

            for attempt in range(self.max_retries):
                try:
                    logger.info(f"Stopping container {self.container_name} (attempt {attempt + 1})")

                    client = self._get_docker_client()
                    container = await asyncio.to_thread(client.containers.get, self.container_name)
                    await asyncio.to_thread(container.stop, timeout=10)

                    if await self.wait_for_state(ContainerState.STOPPED, timeout=15.0):
                        logger.info(f"Successfully stopped container {self.container_name}")
                        return True

                except Exception as e:
                    logger.warning(
                        f"Failed to stop {self.container_name} (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )

                    if attempt < self.max_retries - 1:
                        wait_time = min(2**attempt, 16)
                        await asyncio.sleep(wait_time)

            return False

    async def start_container(self) -> bool:
        """Start container with retry logic."""
        lock = get_container_lock(self.container_name)

        async with lock:
            current_state = await self.get_container_state()
            if current_state == ContainerState.RUNNING:
                logger.info(f"Container {self.container_name} already running")
                return True

            for attempt in range(self.max_retries):
                try:
                    logger.info(f"Starting container {self.container_name} (attempt {attempt + 1})")

                    client = self._get_docker_client()
                    container = await asyncio.to_thread(client.containers.get, self.container_name)
                    await asyncio.to_thread(container.start)

                    if await self.wait_for_state(ContainerState.RUNNING, timeout=15.0):
                        logger.info(f"Successfully started container {self.container_name}")
                        return True

                except Exception as e:
                    logger.warning(
                        f"Failed to start {self.container_name} (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )

                    if attempt < self.max_retries - 1:
                        wait_time = min(2**attempt, 16)
                        await asyncio.sleep(wait_time)

            return False

    async def ensure_running(self) -> bool:
        """Ensure container is in running state, recovering if necessary.

        Returns
        -------
            True if container is running, False if unable to recover

        """
        current_state = await self.get_container_state()

        if current_state == ContainerState.RUNNING:
            return True
        elif current_state == ContainerState.PAUSED:
            return await self.unpause_container()
        elif current_state == ContainerState.STOPPED:
            return await self.start_container()
        else:
            logger.error(f"Cannot ensure running state for {self.container_name} in state {current_state.value}")
            return False

    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check.

        Returns
        -------
            Dictionary with health status information

        """
        state = await self.get_container_state()
        is_healthy = state == ContainerState.RUNNING

        return {
            "container_name": self.container_name,
            "state": state.value,
            "is_healthy": is_healthy,
            "timestamp": time.time(),
        }


async def ensure_container_running(container_name: str) -> bool:
    """Ensure a container is running, with auto-recovery.

    Args:
    ----
        container_name: Name of the container to check

    Returns:
    -------
        True if container is running or was recovered, False otherwise

    """
    manager = DockerHealthManager(container_name)
    return await manager.ensure_running()


async def cleanup_all_containers() -> None:
    """Ensure all test containers are in running state."""
    containers = ["cos_redis", "cos_postgres_dev"]

    tasks = []
    for container in containers:
        task = ensure_container_running(container)
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for container, result in zip(containers, results, strict=False):
        if isinstance(result, Exception):
            logger.error(f"Failed to ensure {container} is running: {result}")
        elif not result:
            logger.warning(f"Could not ensure {container} is running")
        else:
            logger.info(f"Container {container} is running")
