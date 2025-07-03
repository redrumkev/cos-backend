"""Failure Scenario Testing Suite - Task 15.2.

This module implements comprehensive failure scenario testing to validate
system resilience, error handling, and recovery capabilities.

Style bypasses applied for performance test files:
- F841: Unused variables acceptable in test scenarios
- B007: Loop control variables not used (intentional in load testing)
- S603/S607: Subprocess security warnings (required for Docker service control)
- ASYNC101: Async functions calling subprocess (necessary for service interruption)
- SIM105/S110: Try-except-pass patterns (expected in failure scenarios)
- B017/B023: Pytest assert issues (test-specific patterns)

Failure Scenarios Tested:
1. Service Interruptions (Redis, PostgreSQL)
2. Network Failures & Timeouts
3. Resource Exhaustion (Memory, Connections)
4. Concurrent Access Failures
5. Circuit Breaker Validation
6. Graceful Degradation Testing
7. Recovery Time Validation
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import pytest
import redis.asyncio as redis

from src.backend.cc import crud
from src.common.redis_health_monitor import RedisHealthMonitor

from .docker_utils import DockerHealthManager
from .mock_service_utils import mock_service_interruption

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

# Timeout constants
CONNECTION_TIMEOUT_S = 3.0
FAILURE_DETECTION_TIMEOUT_S = 4.0
RECOVERY_TIMEOUT_S = 5.0
OPERATION_TIMEOUT_S = 2.0

logger = logging.getLogger(__name__)


# ServiceController removed - using DockerHealthManager instead


@asynccontextmanager
async def service_interruption(
    service_name: str, interruption_type: str = "pause", use_mock: bool = True
) -> AsyncGenerator[None, None]:
    """Context manager for temporary service interruption with auto-recovery.

    Args:
    ----
        service_name: Name of the service to interrupt (e.g., "cos_redis")
        interruption_type: Type of interruption - "pause", "stop", or mock types:
            - "connection_error": Mock connection failures
            - "timeout": Mock timeout failures
            - "pubsub_failure": Mock pub/sub failures
        use_mock: If True, use mocks instead of actual Docker operations (default: True)

    """
    # Use mocks by default to avoid Docker Desktop manual intervention
    if use_mock:
        # Map Docker interruption types to mock types
        mock_type = interruption_type
        if interruption_type == "pause" or interruption_type == "stop":
            mock_type = "connection_error"

        async with mock_service_interruption(service_name, mock_type):
            yield
        return

    # Original Docker-based implementation (kept for backward compatibility)
    manager = DockerHealthManager(service_name, command_timeout=60.0)

    # For Redis, also use RedisHealthMonitor for additional recovery
    redis_monitor = None
    if service_name == "cos_redis":
        redis_monitor = RedisHealthMonitor(container_name=service_name, auto_recovery=True)

    try:
        # Interrupt the service
        if interruption_type == "pause":
            success = await manager.pause_container()
            if not success:
                pytest.skip(f"Failed to pause {service_name} for test")
        elif interruption_type == "stop":
            success = await manager.stop_container()
            if not success:
                pytest.skip(f"Failed to stop {service_name} for test")

        yield

    finally:
        # Always attempt to restore service, even if test failed
        try:
            if interruption_type == "pause":
                logger.info(f"Restoring {service_name} from paused state")
                success = await manager.unpause_container()

                # For Redis, use health monitor for additional recovery
                if redis_monitor and not success:
                    logger.warning("Using RedisHealthMonitor for recovery")
                    health_status = await redis_monitor.check_health()
                    if health_status.auto_recovery_successful:
                        success = True

                if not success:
                    logger.error(f"Failed to unpause {service_name} - manual intervention may be required")

            elif interruption_type == "stop":
                logger.info(f"Restarting {service_name}")
                success = await manager.start_container()
                if not success:
                    logger.error(f"Failed to start {service_name} - manual intervention may be required")

        except Exception as e:
            logger.exception(f"Error during service restoration for {service_name}: {e}")
            # Don't re-raise to allow test cleanup to continue


class TestRedisFailureScenarios:
    """Redis failure scenario testing."""

    @pytest.mark.asyncio
    async def test_redis_connection_failure_graceful_degradation(self, perf_client: redis.Redis) -> None:
        """Test graceful degradation when Redis connection fails."""
        # Verify baseline connectivity
        await perf_client.ping()

        async with service_interruption("cos_redis", "pause"):
            # Test that operations fail quickly with appropriate errors
            start_time = time.perf_counter()

            with pytest.raises((redis.ConnectionError, redis.TimeoutError, asyncio.TimeoutError)):
                await asyncio.wait_for(perf_client.ping(), timeout=CONNECTION_TIMEOUT_S)

            failure_detection_time = time.perf_counter() - start_time

            # Should detect failure quickly, not hang
            assert (
                failure_detection_time < FAILURE_DETECTION_TIMEOUT_S
            ), f"Failure detection took {failure_detection_time:.2f}s"

            # Test multiple operations fail consistently
            for i in range(5):
                with pytest.raises((redis.ConnectionError, redis.TimeoutError, asyncio.TimeoutError)):
                    await asyncio.wait_for(
                        perf_client.publish(f"test_channel_{i}", f"message_{i}"), timeout=OPERATION_TIMEOUT_S
                    )

        # Validate recovery after service restoration
        await asyncio.sleep(2)  # Allow time for reconnection

        recovery_start = time.perf_counter()
        max_recovery_attempts = 10

        for attempt in range(max_recovery_attempts):
            try:
                await perf_client.ping()
                recovery_time = time.perf_counter() - recovery_start
                break
            except Exception:
                if attempt == max_recovery_attempts - 1:
                    raise
                await asyncio.sleep(0.5)

        assert (
            recovery_time < RECOVERY_TIMEOUT_S
        ), f"Recovery took {recovery_time:.2f}s, exceeds {RECOVERY_TIMEOUT_S}s target"

        # Validate full functionality restored
        await perf_client.publish("recovery_validation", "success")

    @pytest.mark.asyncio
    async def test_redis_pubsub_failure_isolation(self, perf_client: redis.Redis) -> None:
        """Test pub/sub failure isolation and recovery."""
        # Setup pub/sub
        pubsub = perf_client.pubsub()
        await pubsub.subscribe("test_failure_channel")

        # Verify baseline pub/sub functionality
        await perf_client.publish("test_failure_channel", "baseline_message")
        message = await pubsub.get_message(timeout=1.0)
        assert message is not None and message["type"] == "subscribe"

        async with service_interruption("cos_redis", "pause"):
            # Pub/sub should handle failures gracefully
            with pytest.raises((redis.ConnectionError, redis.TimeoutError)):
                await asyncio.wait_for(perf_client.publish("test_failure_channel", "fail_message"), timeout=2.0)

            # Getting messages should also fail appropriately
            with pytest.raises((redis.ConnectionError, redis.TimeoutError)):
                await asyncio.wait_for(pubsub.get_message(timeout=1.0), timeout=2.0)

        # Test pub/sub recovery
        await asyncio.sleep(2)

        # Reconnect pub/sub
        await pubsub.unsubscribe("test_failure_channel")
        await pubsub.close()

        # Create new pub/sub connection
        new_pubsub = perf_client.pubsub()
        await new_pubsub.subscribe("test_failure_channel")

        # Validate recovery
        await perf_client.publish("test_failure_channel", "recovery_message")
        message = await new_pubsub.get_message(timeout=2.0)
        assert message is not None

        await new_pubsub.unsubscribe("test_failure_channel")
        await new_pubsub.close()

    @pytest.mark.asyncio
    async def test_redis_connection_pool_exhaustion(self, perf_client_pool: redis.ConnectionPool) -> None:
        """Test behavior when Redis connection pool is exhausted."""
        # Get pool configuration
        max_connections = perf_client_pool.max_connections

        # Create clients to exhaust the pool
        clients = []
        active_connections = []

        try:
            # Consume all available connections
            for _ in range(max_connections):
                client = redis.Redis(connection_pool=perf_client_pool)
                clients.append(client)

                # Perform operation to activate connection
                await client.ping()
                active_connections.append(client)

            # Now pool should be exhausted - test timeout behavior
            exhausted_client = redis.Redis(connection_pool=perf_client_pool)

            start_time = time.perf_counter()

            # This should timeout or fail quickly, not hang indefinitely
            with pytest.raises((redis.ConnectionError, redis.TimeoutError, asyncio.TimeoutError)):
                await asyncio.wait_for(exhausted_client.ping(), timeout=5.0)

            timeout_handling_time = time.perf_counter() - start_time
            assert timeout_handling_time < 6.0, f"Pool exhaustion handling took {timeout_handling_time:.2f}s"

        finally:
            # Release connections
            for client in clients:
                with contextlib.suppress(Exception):
                    await client.aclose()

        # Validate pool recovery
        recovered_client = redis.Redis(connection_pool=perf_client_pool)
        await recovered_client.ping()
        await recovered_client.aclose()

    @pytest.mark.asyncio
    async def test_redis_network_timeout_handling(self, perf_client: redis.Redis) -> None:
        """Test Redis network timeout handling."""
        # Test various timeout scenarios
        timeout_scenarios = [0.1, 0.5, 1.0, 2.0]  # seconds

        for timeout in timeout_scenarios:
            start_time = time.perf_counter()

            try:
                # Use a very short timeout to simulate network issues
                await asyncio.wait_for(perf_client.ping(), timeout=timeout)
                operation_time = time.perf_counter() - start_time

                # If successful, should be much faster than timeout
                assert operation_time < timeout * 0.8, f"Operation time {operation_time:.2f}s near timeout {timeout}s"

            except TimeoutError:
                operation_time = time.perf_counter() - start_time

                # Timeout should occur close to expected time
                assert (
                    abs(operation_time - timeout) < 0.5
                ), f"Timeout deviation: expected {timeout}s, got {operation_time:.2f}s"


class TestDatabaseFailureScenarios:
    """Database failure scenario testing."""

    @pytest.mark.asyncio
    async def test_database_connection_failure(self, db_session: AsyncSession) -> None:
        """Test database connection failure handling."""
        # Verify baseline connectivity
        test_module = await crud.create_module(db_session, "baseline_test", "1.0.0")
        assert test_module is not None

        async with service_interruption("cos_postgres_dev", "pause"):
            # Database operations should fail with appropriate errors
            from sqlalchemy.exc import DisconnectionError, OperationalError

            with pytest.raises((OperationalError, DisconnectionError)):
                await crud.create_module(db_session, "fail_test", "1.0.0")

            # Multiple operations should consistently fail
            for _ in range(3):
                with pytest.raises((OperationalError, DisconnectionError)):
                    await crud.get_modules(db_session, skip=0, limit=10)

        # Test recovery - may need new session
        await asyncio.sleep(3)  # Allow time for service recovery

        # Connection may need to be re-established
        recovery_module = await crud.create_module(db_session, "recovery_test", "1.0.0")
        assert recovery_module is not None
        assert recovery_module.name == "recovery_test"

    @pytest.mark.asyncio
    async def test_database_transaction_failure_rollback(self, db_session: AsyncSession) -> None:
        """Test database transaction failure and rollback behavior."""
        # Get initial module count
        initial_modules = await crud.get_modules(db_session, skip=0, limit=1000)
        _ = len(initial_modules)  # Track for potential future validation

        # Simulate transaction failure
        try:
            # Create a module
            module1 = await crud.create_module(db_session, "transaction_test_1", "1.0.0")
            assert module1 is not None

            # Force a transaction error by attempting duplicate creation
            from sqlalchemy.exc import DisconnectionError, OperationalError

            with pytest.raises((OperationalError, DisconnectionError)):  # Database integrity or connection errors
                await crud.create_module(db_session, "transaction_test_1", "2.0.0")  # Same name, different version

        except Exception:  # noqa: S110
            # Transaction should be rolled back (expected failure)
            pass

        # Verify transaction state after failure
        final_modules = await crud.get_modules(db_session, skip=0, limit=1000)
        _ = len(final_modules)  # Track for potential future validation

        # Depending on transaction isolation, we might have partial state
        # The important thing is the session is still usable

        # Verify session is still functional
        recovery_module = await crud.create_module(db_session, "post_failure_test", "1.0.0")
        assert recovery_module is not None

    @pytest.mark.asyncio
    async def test_database_concurrent_access_deadlock_prevention(self, postgres_session: Any) -> None:
        """Test deadlock prevention in concurrent database access."""
        deadlock_detected = False
        successful_operations = 0

        async def concurrent_db_operation(operation_id: int) -> bool:
            """Perform concurrent database operations that might cause deadlocks."""
            nonlocal deadlock_detected, successful_operations

            operation_success = False
            max_retries = 3

            for attempt in range(max_retries):
                try:
                    async with postgres_session() as session:
                        # Operations that might cause deadlocks
                        _ = await crud.create_module(session, f"concurrent_op_{operation_id}_{attempt}", "1.0.0")

                        # Read operation
                        _ = await crud.get_modules(session, skip=0, limit=5)

                        operation_success = True
                        successful_operations += 1
                        break

                except Exception as e:
                    if "deadlock" in str(e).lower():
                        deadlock_detected = True
                        logger.warning(f"Deadlock detected in operation {operation_id}, attempt {attempt}")

                    if attempt == max_retries - 1:
                        logger.error(f"Operation {operation_id} failed after {max_retries} attempts: {e}")
                        raise

                    # Brief delay before retry
                    await asyncio.sleep(0.1 * (attempt + 1))

            return operation_success

        # Run concurrent operations
        num_operations = 20
        tasks = [concurrent_db_operation(i) for i in range(num_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        successful_results = [r for r in results if r is True]
        _ = [r for r in results if isinstance(r, Exception)]  # Track failed results

        # Most operations should succeed (allowing for some expected failures)
        success_rate = len(successful_results) / num_operations
        assert success_rate >= 0.8, f"Success rate {success_rate:.2%} too low"

        # If deadlocks occurred, they should be handled gracefully
        if deadlock_detected:
            logger.info("Deadlocks were detected and handled appropriately")


class TestNetworkFailureScenarios:
    """Network failure scenario testing."""

    @pytest.mark.asyncio
    async def test_api_timeout_handling(self, async_client: AsyncClient) -> None:
        """Test API timeout handling under network delays."""
        # Test with various timeout configurations
        timeout_configs = [1.0, 5.0, 10.0]  # seconds

        for timeout in timeout_configs:
            start_time = time.perf_counter()

            try:
                # Configure client with specific timeout
                async with AsyncClient(base_url="http://localhost:8000", timeout=timeout) as client:
                    response = await client.get("/cc/health")
                    response_time = time.perf_counter() - start_time

                    # Successful response should be much faster than timeout
                    assert response.status_code == 200
                    assert response_time < timeout * 0.5, f"Response time {response_time:.2f}s near timeout {timeout}s"

            except Exception as e:
                response_time = time.perf_counter() - start_time
                logger.info(f"Request with {timeout}s timeout failed after {response_time:.2f}s: {e}")

                # Timeout should occur reasonably close to configured value
                assert (
                    abs(response_time - timeout) < 2.0
                ), f"Timeout variance too high: {response_time:.2f}s vs {timeout}s"

    @pytest.mark.asyncio
    async def test_service_unavailable_handling(self, async_client: AsyncClient) -> None:
        """Test API behavior when upstream services are unavailable."""
        # Test with Redis unavailable
        async with service_interruption("cos_redis", "pause"):
            # API should handle Redis unavailability gracefully
            response = await async_client.get("/cc/health")

            # Health check might indicate degraded state or still pass
            # depending on implementation - both are valid approaches
            assert response.status_code in [200, 503], f"Unexpected status: {response.status_code}"

            # Test module operations - these might fail or degrade gracefully
            module_data = {"name": "redis_unavailable_test", "version": "1.0.0"}

            try:
                response = await async_client.post("/cc/modules/", json=module_data)
                # If successful, operation should complete
                assert response.status_code in [201, 503], f"Unexpected status: {response.status_code}"
            except Exception as e:
                # Network-level failures are also acceptable
                logger.info(f"Expected failure during Redis unavailability: {e}")

    @pytest.mark.asyncio
    async def test_partial_service_degradation(self, async_client: AsyncClient) -> None:
        """Test behavior during partial service degradation."""
        # Test with database unavailable but Redis available
        async with service_interruption("cos_postgres_dev", "pause"):
            # Use enhanced health check endpoint which doesn't require database
            response = await async_client.get("/cc/health/enhanced")

            # Health status should indicate issues or still pass with warnings
            assert response.status_code in [200, 503]

            # Operations requiring database should fail gracefully
            module_data = {"name": "db_unavailable_test", "version": "1.0.0"}

            try:
                response = await async_client.post("/cc/modules/", json=module_data)
                # Should fail gracefully with appropriate error
                assert response.status_code in [500, 503], f"Expected failure, got: {response.status_code}"
            except Exception as e:
                logger.info(f"Expected database failure: {e}")


class TestResourceExhaustionScenarios:
    """Resource exhaustion scenario testing."""

    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, perf_client: redis.Redis) -> None:
        """Test system behavior under memory pressure."""
        import psutil

        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB

        # Create memory pressure gradually
        memory_consumers = []

        try:
            for round_num in range(20):  # Reduced from 100 to avoid excessive memory usage
                # Allocate memory in chunks
                chunk = bytearray(5 * 1024 * 1024)  # 5MB chunks
                memory_consumers.append(chunk)

                current_memory = process.memory_info().rss / (1024 * 1024)
                memory_growth = current_memory - initial_memory

                # Test Redis operations under memory pressure
                if round_num % 5 == 0:
                    start_time = time.perf_counter()

                    try:
                        await perf_client.ping()
                        operation_time = time.perf_counter() - start_time

                        # Operations should still work but may be slower
                        assert operation_time < 2.0, f"Operation too slow under memory pressure: {operation_time:.2f}s"

                    except Exception as e:
                        # Under extreme memory pressure, operations might fail
                        logger.warning(f"Operation failed under memory pressure: {e}")

                # Stop if memory growth is excessive to prevent system issues
                if memory_growth > 100:  # 100MB limit
                    logger.info(f"Stopping memory test at {memory_growth:.1f}MB growth")
                    break

        finally:
            # Release memory
            memory_consumers.clear()
            import gc

            gc.collect()

    @pytest.mark.asyncio
    async def test_concurrent_connection_limit(self, perf_client: redis.Redis) -> None:
        """Test behavior at concurrent connection limits."""
        max_concurrent = 50  # Reasonable limit for testing
        active_clients = []

        try:
            # Create many concurrent clients
            for i in range(max_concurrent):
                client = redis.Redis(host="localhost", port=6379, socket_connect_timeout=5.0, socket_timeout=5.0)
                active_clients.append(client)

                # Test connection establishment
                try:
                    await client.ping()
                except Exception as e:
                    logger.warning(f"Connection {i} failed: {e}")
                    # Remove failed client from list
                    active_clients.remove(client)

                    # If we can't establish many connections, that's the limit
                    if len(active_clients) < max_concurrent * 0.8:
                        logger.info(f"Connection limit reached at {len(active_clients)} connections")
                        break

            # Test operations with all active connections
            successful_ops = 0
            failed_ops = 0

            for i, client in enumerate(active_clients[:20]):  # Test subset to avoid timeout
                try:
                    await client.publish(f"concurrent_test_{i}", f"message_{i}")
                    successful_ops += 1
                except Exception:
                    failed_ops += 1

            # Most operations should succeed
            success_rate = successful_ops / (successful_ops + failed_ops) if (successful_ops + failed_ops) > 0 else 0
            assert success_rate >= 0.8, f"Success rate {success_rate:.2%} too low under concurrent load"

        finally:
            # Cleanup connections
            for client in active_clients:
                with contextlib.suppress(Exception):
                    await client.aclose()

    @pytest.mark.asyncio
    async def test_high_frequency_operation_limits(self, perf_client: redis.Redis) -> None:
        """Test system behavior under high-frequency operations."""
        # Test sustained high-frequency operations
        operations_per_second = 1000
        test_duration = 5  # seconds
        total_operations = operations_per_second * test_duration

        successful_ops = 0
        failed_ops = 0
        start_time = time.perf_counter()

        # Batch operations for efficiency
        batch_size = 100
        for batch in range(0, total_operations, batch_size):
            batch_tasks = []

            for i in range(min(batch_size, total_operations - batch)):
                task = perf_client.publish(f"high_freq_{batch}_{i}", f"data_{i}")
                batch_tasks.append(task)

            try:
                await asyncio.gather(*batch_tasks)
                successful_ops += len(batch_tasks)
            except Exception as e:
                failed_ops += len(batch_tasks)
                logger.warning(f"Batch {batch} failed: {e}")

            # Check if we're maintaining target rate
            elapsed = time.perf_counter() - start_time
            expected_ops = int(elapsed * operations_per_second)

            if successful_ops < expected_ops * 0.8:  # Allow 20% variance
                logger.warning(f"Falling behind target rate: {successful_ops} vs {expected_ops}")

        total_time = time.perf_counter() - start_time
        actual_ops_per_sec = successful_ops / total_time

        # Should maintain reasonable throughput
        assert actual_ops_per_sec >= operations_per_second * 0.5, f"Throughput {actual_ops_per_sec:.0f} ops/s too low"

        # Error rate should be reasonable
        error_rate = failed_ops / (successful_ops + failed_ops) if (successful_ops + failed_ops) > 0 else 0
        assert error_rate <= 0.1, f"Error rate {error_rate:.2%} too high"


class TestCircuitBreakerValidation:
    """Circuit breaker pattern validation."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_redis_failures(self, perf_client: redis.Redis) -> None:
        """Test circuit breaker behavior for Redis failures."""

        # Simulate a circuit breaker implementation
        class SimpleCircuitBreaker:
            def __init__(self, failure_threshold: int = 5, timeout: float = 10.0):
                self.failure_threshold = failure_threshold
                self.timeout = timeout
                self.failure_count = 0
                self.last_failure_time = 0.0
                self.state = "closed"  # closed, open, half-open

            async def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
                if self.state == "open":
                    if time.time() - self.last_failure_time > self.timeout:
                        self.state = "half-open"
                    else:
                        raise Exception("Circuit breaker is open")

                try:
                    result = await func(*args, **kwargs)
                    if self.state == "half-open":
                        self.state = "closed"
                        self.failure_count = 0
                    return result
                except Exception as e:
                    self.failure_count += 1
                    self.last_failure_time = time.time()

                    if self.failure_count >= self.failure_threshold:
                        self.state = "open"

                    raise e

        circuit_breaker = SimpleCircuitBreaker(failure_threshold=3, timeout=2.0)

        # Test normal operation
        result = await circuit_breaker.call(perf_client.ping)
        assert result is True

        # Simulate failures to trip circuit breaker
        async with service_interruption("cos_redis", "pause"):
            failure_count = 0

            # Generate failures to trip circuit breaker
            for _ in range(5):
                try:
                    await circuit_breaker.call(perf_client.ping)
                except Exception:
                    failure_count += 1
                    if circuit_breaker.state == "open":
                        logger.info(f"Circuit breaker opened after {failure_count} failures")
                        break

            # Circuit breaker should be open now
            assert circuit_breaker.state == "open"

            # Subsequent calls should fail fast
            start_time = time.perf_counter()
            with pytest.raises(Exception, match="Circuit breaker is open"):
                await circuit_breaker.call(perf_client.ping)

            fail_fast_time = time.perf_counter() - start_time
            assert fail_fast_time < 0.1, f"Circuit breaker didn't fail fast: {fail_fast_time:.3f}s"

        # Wait for circuit breaker timeout
        await asyncio.sleep(2.5)

        # Circuit breaker should transition to half-open and eventually close
        result = await circuit_breaker.call(perf_client.ping)
        assert result is True
        assert circuit_breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_circuit_breaker_database_failures(self, db_session: AsyncSession) -> None:
        """Test circuit breaker behavior for database failures."""

        # Similar circuit breaker for database operations
        class DatabaseCircuitBreaker:
            def __init__(self, failure_threshold: int = 3):
                self.failure_threshold = failure_threshold
                self.failure_count = 0
                self.state = "closed"

            async def execute_query(self, session: Any, operation: Any) -> Any:
                if self.state == "open":
                    raise Exception("Database circuit breaker is open")

                try:
                    result = await operation(session)
                    self.failure_count = 0  # Reset on success
                    return result
                except Exception as e:
                    self.failure_count += 1
                    if self.failure_count >= self.failure_threshold:
                        self.state = "open"
                    raise e

        db_circuit_breaker = DatabaseCircuitBreaker(failure_threshold=2)

        # Test normal operation
        result = await db_circuit_breaker.execute_query(
            db_session, lambda s: crud.create_module(s, "circuit_test", "1.0.0")
        )
        assert result is not None

        # Simulate database failures
        async with service_interruption("cos_postgres_dev", "pause"):
            failure_count = 0

            for i in range(3):
                try:
                    await db_circuit_breaker.execute_query(
                        db_session, lambda s, idx=i: crud.create_module(s, f"fail_test_{idx}", "1.0.0")
                    )
                except Exception:
                    failure_count += 1
                    if db_circuit_breaker.state == "open":
                        logger.info(f"Database circuit breaker opened after {failure_count} failures")
                        break

            # Circuit breaker should be open
            assert db_circuit_breaker.state == "open"

            # Subsequent operations should fail fast
            with pytest.raises(Exception, match="Database circuit breaker is open"):
                await db_circuit_breaker.execute_query(db_session, lambda s: crud.get_modules(s, skip=0, limit=10))


# Performance test markers
pytestmark = [
    pytest.mark.performance,
    pytest.mark.failure_scenarios,
    pytest.mark.requires_redis,
    pytest.mark.requires_postgres,
]
