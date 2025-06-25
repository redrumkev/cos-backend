"""Production Readiness Performance Tests - Task 15.2.

Comprehensive performance benchmarking and failure scenario testing
to validate Phase 2 Sprint 2 production readiness.

Style bypasses applied for performance test files:
- D400/D415: Docstring formatting (relaxed for test files)
- S106: Hardcoded password (test credentials only)
- D401: Docstring imperative mood (acceptable in test descriptions)
- B007: Loop control variables (intentional in performance loops)
- E501: Line too long (acceptable for test data/assertions)
- ASYNC101/S603/S607: Subprocess issues (required for service control)

Key Performance Targets:
- API response times: P50 < 100ms, P95 < 500ms, P99 < 1000ms
- Redis pub/sub latency: < 5ms average
- Redis throughput: ≥ 1000 msg/s
- Database query performance: < 100ms for standard operations
- Memory usage: No leaks, stable under load
- Recovery time: < 10s after service restoration

Failure Scenarios:
- Service interruptions (Redis, PostgreSQL)
- Network timeouts
- Resource exhaustion
- Circuit breaker validation

# mypy: ignore-errors

# ruff: noqa
"""

from __future__ import annotations

import asyncio
import gc
import logging
import shutil
import subprocess
import time
from typing import Any

import psutil
import pytest
import redis.asyncio as redis
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc import crud

logger = logging.getLogger(__name__)


@pytest.fixture
async def redis_client() -> redis.Redis:
    """Redis client with authentication for performance testing."""
    client = redis.Redis(
        host="localhost",
        port=6379,
        password="Police9119!!Red",  # noqa: S106
        decode_responses=True,
        socket_keepalive=True,
        socket_connect_timeout=5.0,
        socket_timeout=5.0,
    )
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
async def http_client() -> AsyncClient:
    """HTTP client for API testing."""
    async with AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        yield client


# ---------------------------------------------------------------------------
# Docker helpers
# ---------------------------------------------------------------------------


async def run_docker_command(*args: str) -> None:
    """Run a docker CLI command asynchronously.

    This helper prevents blocking the event-loop (addresses ASYNC101) and also
    ensures an absolute docker executable path is used (addresses S607).
    """
    docker_path = shutil.which("docker")
    if docker_path is None:
        raise RuntimeError("`docker` executable not found - required for integration tests.")

    proc = await asyncio.create_subprocess_exec(
        docker_path,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        cmd_list = [docker_path, *args]
        raise subprocess.CalledProcessError(proc.returncode, cmd_list, output=stdout, stderr=stderr)


class PerformanceMetrics:
    """Simple performance metrics collector."""

    def __init__(self) -> None:
        self.measurements = {}

    def record(self, metric_name: str, value: float, unit: str = "ms") -> None:
        """Record a performance measurement."""
        if metric_name not in self.measurements:
            self.measurements[metric_name] = []
        self.measurements[metric_name].append({"value": value, "unit": unit, "timestamp": time.time()})

    def get_stats(self, metric_name: str) -> dict[str, float]:
        """Get statistics for a metric."""
        if metric_name not in self.measurements:
            return {}

        values = [m["value"] for m in self.measurements[metric_name]]
        if not values:
            return {}

        sorted_values = sorted(values)
        n = len(sorted_values)

        return {
            "mean": sum(values) / n,
            "median": sorted_values[n // 2],
            "p95": sorted_values[int(0.95 * n)],
            "p99": sorted_values[int(0.99 * n)],
            "min": min(values),
            "max": max(values),
            "count": n,
        }


@pytest.fixture
def metrics() -> PerformanceMetrics:
    """Provide performance metrics collector."""
    return PerformanceMetrics()


class TestRedisPerformance:
    """Redis performance benchmarks."""

    @pytest.mark.asyncio
    async def test_redis_latency_performance(self, redis_client: redis.Redis, metrics: PerformanceMetrics) -> None:
        """Test Redis latency meets performance targets."""
        # Warmup
        for _ in range(10):
            await redis_client.ping()

        # Measure latency
        latencies = []
        for _ in range(1000):
            start = time.perf_counter_ns()
            await redis_client.ping()
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            latencies.append(latency_ms)
            metrics.record("redis_ping_latency", latency_ms)

        stats = metrics.get_stats("redis_ping_latency")

        # Performance assertions
        assert stats["mean"] < 5.0, f"Redis mean latency {stats['mean']:.2f}ms > 5ms"
        assert stats["p95"] < 10.0, f"Redis P95 latency {stats['p95']:.2f}ms > 10ms"
        assert stats["p99"] < 20.0, f"Redis P99 latency {stats['p99']:.2f}ms > 20ms"

        logger.info(
            f"Redis Latency - Mean: {stats['mean']:.2f}ms, P95: {stats['p95']:.2f}ms, P99: {stats['p99']:.2f}ms"
        )

    @pytest.mark.asyncio
    async def test_redis_throughput_performance(self, redis_client: redis.Redis, metrics: PerformanceMetrics) -> None:
        """Test Redis throughput meets performance targets."""
        # Throughput test
        message_count = 2000
        start_time = time.perf_counter()

        # Batch publish operations
        tasks = []
        for i in range(message_count):
            task = redis_client.publish(f"perf_channel_{i % 10}", f"message_{i}")
            tasks.append(task)

        await asyncio.gather(*tasks)

        duration = time.perf_counter() - start_time
        throughput = message_count / duration

        metrics.record("redis_throughput", throughput, "msg/s")

        # Performance assertion
        assert throughput >= 1000, f"Redis throughput {throughput:.0f} msg/s < 1000 msg/s"

        logger.info(f"Redis Throughput: {throughput:.0f} msg/s in {duration:.2f}s")

    @pytest.mark.asyncio
    async def test_redis_pubsub_latency(self, redis_client: redis.Redis, metrics: PerformanceMetrics) -> None:
        """Test Redis pub/sub latency."""
        # Setup pub/sub
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("latency_test_channel")

        # Skip subscription confirmation
        message = await pubsub.get_message(timeout=1.0)
        assert message and message["type"] == "subscribe"

        latencies = []

        # Measure pub/sub latency
        for _ in range(100):
            # Publish message with timestamp
            publish_time = time.perf_counter_ns()
            await redis_client.publish("latency_test_channel", str(publish_time))

            # Receive message
            message = await pubsub.get_message(timeout=2.0)
            receive_time = time.perf_counter_ns()

            if message and message["type"] == "message":
                sent_time = int(message["data"])
                latency_ms = (receive_time - sent_time) / 1_000_000
                latencies.append(latency_ms)
                metrics.record("redis_pubsub_latency", latency_ms)

        await pubsub.unsubscribe("latency_test_channel")
        await pubsub.close()

        if latencies:
            stats = metrics.get_stats("redis_pubsub_latency")
            assert stats["mean"] < 10.0, f"Pub/sub mean latency {stats['mean']:.2f}ms > 10ms"
            logger.info(f"Redis Pub/Sub Latency - Mean: {stats['mean']:.2f}ms, P95: {stats['p95']:.2f}ms")


class TestDatabasePerformance:
    """Database performance benchmarks."""

    @pytest.mark.asyncio
    async def test_database_query_performance(self, db_session: AsyncSession, metrics: PerformanceMetrics) -> None:
        """Test database query performance."""
        # Create test data
        for i in range(20):
            await crud.create_module(db_session, f"perf_test_module_{i}", "1.0.0")

        # Test read performance
        read_latencies = []
        for _ in range(100):
            start = time.perf_counter_ns()
            modules = await crud.get_modules(db_session, skip=0, limit=10)
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            read_latencies.append(latency_ms)
            metrics.record("db_read_latency", latency_ms)
            assert len(modules) > 0

        # Test write performance
        write_latencies = []
        for i in range(50):
            start = time.perf_counter_ns()
            module = await crud.create_module(db_session, f"write_perf_test_{i}", "1.0.0")
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            write_latencies.append(latency_ms)
            metrics.record("db_write_latency", latency_ms)
            assert module is not None

        # Performance assertions
        read_stats = metrics.get_stats("db_read_latency")
        write_stats = metrics.get_stats("db_write_latency")

        assert read_stats["mean"] < 50.0, f"DB read mean latency {read_stats['mean']:.2f}ms > 50ms"
        assert write_stats["mean"] < 100.0, f"DB write mean latency {write_stats['mean']:.2f}ms > 100ms"

        logger.info(f"Database Read - Mean: {read_stats['mean']:.2f}ms, P95: {read_stats['p95']:.2f}ms")
        logger.info(f"Database Write - Mean: {write_stats['mean']:.2f}ms, P95: {write_stats['p95']:.2f}ms")

    @pytest.mark.asyncio
    async def test_database_concurrent_performance(self, postgres_session, metrics: PerformanceMetrics) -> None:
        """Test database performance under concurrent load."""

        async def concurrent_operations(task_id: int) -> float:
            """Perform concurrent database operations."""
            start = time.perf_counter()

            async with postgres_session() as session:
                # Mixed read/write operations
                for i in range(10):
                    if i % 3 == 0:
                        # Write operation
                        module = await crud.create_module(session, f"concurrent_{task_id}_{i}", "1.0.0")
                        assert module is not None
                    else:
                        # Read operation
                        modules = await crud.get_modules(session, skip=0, limit=5)
                        assert len(modules) >= 0

            return time.perf_counter() - start

        # Run concurrent tasks
        num_tasks = 10
        start_time = time.perf_counter()

        tasks = [concurrent_operations(i) for i in range(num_tasks)]
        task_times = await asyncio.gather(*tasks)

        total_time = time.perf_counter() - start_time
        avg_task_time = sum(task_times) / len(task_times)

        metrics.record("db_concurrent_task_time", avg_task_time * 1000)  # Convert to ms

        # Performance assertions
        assert total_time < 10.0, f"Concurrent DB operations took {total_time:.2f}s > 10s"
        assert avg_task_time < 2.0, f"Average task time {avg_task_time:.2f}s > 2s"

        logger.info(f"Database Concurrent - {num_tasks} tasks in {total_time:.2f}s, avg {avg_task_time:.2f}s per task")


class TestAPIPerformance:
    """API performance benchmarks."""

    @pytest.mark.asyncio
    async def test_api_endpoint_performance(self, http_client: AsyncClient, metrics: PerformanceMetrics) -> None:
        """Test API endpoint performance."""
        # Test health endpoint
        health_latencies = []
        for _ in range(100):
            start = time.perf_counter_ns()
            response = await http_client.get("/cc/health")
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            health_latencies.append(latency_ms)
            metrics.record("api_health_latency", latency_ms)
            assert response.status_code == 200

        # Test module creation endpoint
        create_latencies = []
        for i in range(20):
            module_data = {"name": f"api_perf_module_{i}", "version": "1.0.0"}
            start = time.perf_counter_ns()
            response = await http_client.post("/cc/modules/", json=module_data)
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            create_latencies.append(latency_ms)
            metrics.record("api_create_latency", latency_ms)
            assert response.status_code == 201

        # Test list modules endpoint
        list_latencies = []
        for _ in range(50):
            start = time.perf_counter_ns()
            response = await http_client.get("/cc/modules/")
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            list_latencies.append(latency_ms)
            metrics.record("api_list_latency", latency_ms)
            assert response.status_code == 200

        # Performance assertions
        health_stats = metrics.get_stats("api_health_latency")
        create_stats = metrics.get_stats("api_create_latency")
        list_stats = metrics.get_stats("api_list_latency")

        assert health_stats["p95"] < 100.0, f"API health P95 {health_stats['p95']:.2f}ms > 100ms"
        assert create_stats["p95"] < 500.0, f"API create P95 {create_stats['p95']:.2f}ms > 500ms"
        assert list_stats["p95"] < 200.0, f"API list P95 {list_stats['p95']:.2f}ms > 200ms"

        logger.info(f"API Health - Mean: {health_stats['mean']:.2f}ms, P95: {health_stats['p95']:.2f}ms")
        logger.info(f"API Create - Mean: {create_stats['mean']:.2f}ms, P95: {create_stats['p95']:.2f}ms")
        logger.info(f"API List - Mean: {list_stats['mean']:.2f}ms, P95: {list_stats['p95']:.2f}ms")

    @pytest.mark.asyncio
    async def test_api_concurrent_load(self, http_client: AsyncClient, metrics: PerformanceMetrics) -> None:
        """Test API performance under concurrent load."""

        async def concurrent_requests(client_id: int) -> dict[str, Any]:
            """Execute concurrent API requests."""
            results = {"success": 0, "errors": 0, "latencies": []}

            for _ in range(20):
                try:
                    start = time.perf_counter_ns()
                    response = await http_client.get("/cc/health")
                    latency_ms = (time.perf_counter_ns() - start) / 1_000_000

                    if response.status_code == 200:
                        results["success"] += 1
                        results["latencies"].append(latency_ms)
                        metrics.record("api_concurrent_latency", latency_ms)
                    else:
                        results["errors"] += 1
                except Exception:
                    results["errors"] += 1

            return results

        # Run concurrent requests
        num_clients = 10
        start_time = time.perf_counter()

        tasks = [concurrent_requests(i) for i in range(num_clients)]
        results = await asyncio.gather(*tasks)

        total_time = time.perf_counter() - start_time

        # Aggregate results
        total_success = sum(r["success"] for r in results)
        total_errors = sum(r["errors"] for r in results)
        throughput = total_success / total_time

        # Performance assertions
        error_rate = total_errors / (total_success + total_errors) if (total_success + total_errors) > 0 else 0
        assert error_rate < 0.05, f"API error rate {error_rate:.2%} > 5%"
        assert throughput > 50, f"API throughput {throughput:.0f} req/s < 50 req/s"

        concurrent_stats = metrics.get_stats("api_concurrent_latency")
        if concurrent_stats:
            assert concurrent_stats["p95"] < 1000.0, f"API concurrent P95 {concurrent_stats['p95']:.2f}ms > 1000ms"

        logger.info(
            f"API Concurrent - {total_success} requests in {total_time:.2f}s, "
            f"{throughput:.0f} req/s, {error_rate:.2%} errors"
        )


class TestMemoryAndResourceUsage:
    """Memory and resource usage tests."""

    @pytest.mark.asyncio
    async def test_memory_stability_under_load(self, redis_client: redis.Redis, metrics: PerformanceMetrics) -> None:
        """Test memory stability under sustained load."""
        process = psutil.Process()

        # Baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / (1024 * 1024)  # MB

        # Sustained operations
        for cycle in range(50):
            # Batch operations
            tasks = []
            for i in range(100):
                message_data = f"cycle_{cycle}_msg_{i}_" + "x" * 50
                task = redis_client.publish(f"memory_test_{cycle % 5}", message_data)
                tasks.append(task)

            await asyncio.gather(*tasks)

            # Memory monitoring
            if cycle % 10 == 0:
                gc.collect()
                current_memory = process.memory_info().rss / (1024 * 1024)
                memory_growth = current_memory - baseline_memory
                metrics.record("memory_usage", current_memory, "MB")
                metrics.record("memory_growth", memory_growth, "MB")

                logger.info(f"Cycle {cycle}: Memory {current_memory:.1f}MB (+{memory_growth:.1f}MB)")

                # Memory growth should be reasonable
                assert memory_growth < 100, f"Excessive memory growth: {memory_growth:.1f}MB"

        # Final memory check
        gc.collect()
        final_memory = process.memory_info().rss / (1024 * 1024)
        total_growth = final_memory - baseline_memory

        assert total_growth < 50, f"Total memory growth {total_growth:.1f}MB excessive"
        logger.info(f"Memory Test Complete - Growth: {total_growth:.1f}MB")

    @pytest.mark.asyncio
    async def test_cpu_usage_under_load(self, redis_client: redis.Redis, metrics: PerformanceMetrics) -> None:
        """Test CPU usage under load."""
        process = psutil.Process()
        cpu_samples = []

        # CPU-intensive operations
        for batch in range(20):
            # High-frequency operations
            start_time = time.perf_counter()

            tasks = []
            for i in range(200):
                task = redis_client.publish(f"cpu_test_{i % 10}", f"batch_{batch}_msg_{i}")
                tasks.append(task)

            await asyncio.gather(*tasks)

            # Sample CPU usage
            cpu_percent = process.cpu_percent()
            cpu_samples.append(cpu_percent)
            metrics.record("cpu_usage", cpu_percent, "%")

            if batch % 5 == 0:
                batch_time = time.perf_counter() - start_time
                logger.info(f"Batch {batch}: CPU {cpu_percent:.1f}%, Time {batch_time:.2f}s")

        # CPU usage analysis
        if cpu_samples:
            avg_cpu = sum(cpu_samples) / len(cpu_samples)
            max_cpu = max(cpu_samples)

            # Reasonable CPU usage under load
            assert avg_cpu < 80.0, f"Average CPU usage {avg_cpu:.1f}% too high"
            assert max_cpu < 95.0, f"Peak CPU usage {max_cpu:.1f}% too high"

            logger.info(f"CPU Usage - Average: {avg_cpu:.1f}%, Peak: {max_cpu:.1f}%")


class TestFailureScenarios:
    """Failure scenario and recovery testing."""

    @pytest.mark.asyncio
    async def test_redis_service_interruption_recovery(
        self, redis_client: redis.Redis, metrics: PerformanceMetrics
    ) -> None:
        """Test Redis service interruption and recovery."""
        # Verify baseline connectivity
        await redis_client.ping()
        logger.info("Redis baseline connectivity verified")

        try:
            # Pause Redis service
            await run_docker_command("pause", "cos_redis")
            logger.info("Redis service paused for failure simulation")

            # Test failure detection
            failure_start = time.perf_counter()

            with pytest.raises((redis.ConnectionError, redis.TimeoutError, asyncio.TimeoutError)):
                await asyncio.wait_for(redis_client.ping(), timeout=5.0)

            failure_detection_time = time.perf_counter() - failure_start
            metrics.record("failure_detection_time", failure_detection_time * 1000)

            assert failure_detection_time < 6.0, f"Failure detection took {failure_detection_time:.2f}s"
            logger.info(f"Redis failure detected in {failure_detection_time:.2f}s")

        finally:
            # Restore Redis service
            await run_docker_command("unpause", "cos_redis")
            logger.info("Redis service restored")

            # Test recovery
            recovery_start = time.perf_counter()
            max_recovery_attempts = 20

            for attempt in range(max_recovery_attempts):
                try:
                    await redis_client.ping()
                    recovery_time = time.perf_counter() - recovery_start
                    metrics.record("recovery_time", recovery_time * 1000)
                    logger.info(f"Redis recovery successful in {recovery_time:.2f}s")
                    break
                except Exception:
                    if attempt == max_recovery_attempts - 1:
                        raise
                    await asyncio.sleep(0.5)

            # Recovery should be quick
            assert recovery_time < 10.0, f"Recovery time {recovery_time:.2f}s > 10s"

            # Validate functionality restored
            await redis_client.publish("recovery_test", "functionality_restored")
            logger.info("Redis functionality fully restored")

    @pytest.mark.asyncio
    async def test_high_error_rate_handling(self, redis_client: redis.Redis, metrics: PerformanceMetrics) -> None:
        """Test system behavior under high error conditions."""
        # Simulate circuit breaker behavior
        consecutive_failures = 0
        circuit_open = False

        async def protected_operation(operation_id: int) -> bool:
            """Simulate operation with circuit breaker pattern."""
            nonlocal consecutive_failures, circuit_open

            # Circuit breaker logic
            if circuit_open:
                # Fail fast when circuit is open
                raise Exception("Circuit breaker is open")

            try:
                # Simulate intermittent failures
                if operation_id % 3 == 0 and operation_id < 15:
                    consecutive_failures += 1
                    if consecutive_failures >= 5:
                        circuit_open = True
                        logger.info("Circuit breaker opened")
                    raise redis.ConnectionError("Simulated failure")
                else:
                    # Successful operation
                    await redis_client.ping()
                    consecutive_failures = 0
                    return True

            except Exception:
                consecutive_failures += 1
                raise

        # Test circuit breaker behavior
        success_count = 0
        failure_count = 0

        for i in range(30):
            start = time.perf_counter_ns()

            try:
                result = await protected_operation(i)
                if result:
                    success_count += 1
                operation_time = (time.perf_counter_ns() - start) / 1_000_000
                metrics.record("protected_operation_time", operation_time)

            except Exception as e:
                failure_count += 1
                operation_time = (time.perf_counter_ns() - start) / 1_000_000

                if "Circuit breaker" in str(e):
                    # Circuit breaker should fail fast
                    assert operation_time < 1.0, f"Circuit breaker fail-fast took {operation_time:.2f}ms"
                    metrics.record("circuit_breaker_fail_time", operation_time)

        # Validate error handling
        total_ops = success_count + failure_count
        error_rate = failure_count / total_ops if total_ops > 0 else 0

        logger.info(
            f"Error handling test - Success: {success_count}, Failures: {failure_count}, Error rate: {error_rate:.2%}"
        )

        # Circuit breaker should have activated
        assert circuit_open, "Circuit breaker should have opened under failure conditions"
        assert success_count > 0, "Some operations should succeed"


@pytest.mark.asyncio
async def test_comprehensive_performance_report(
    redis_client: redis.Redis, db_session: AsyncSession, http_client: AsyncClient, metrics: PerformanceMetrics
) -> None:
    """Generate comprehensive performance report."""
    logger.info("=== COMPREHENSIVE PERFORMANCE REPORT - TASK 15.2 ===")

    # Run basic performance validation
    start_time = time.time()

    # Quick Redis test
    await redis_client.ping()
    redis_start = time.perf_counter_ns()
    await redis_client.publish("report_test", "performance_validation")
    redis_latency = (time.perf_counter_ns() - redis_start) / 1_000_000

    # Quick DB test
    db_start = time.perf_counter_ns()
    modules = await crud.get_modules(db_session, skip=0, limit=5)
    db_latency = (time.perf_counter_ns() - db_start) / 1_000_000

    # Quick API test
    api_start = time.perf_counter_ns()
    response = await http_client.get("/cc/health")
    api_latency = (time.perf_counter_ns() - api_start) / 1_000_000

    total_time = time.time() - start_time

    # System resource snapshot
    process = psutil.Process()
    memory_mb = process.memory_info().rss / (1024 * 1024)
    cpu_percent = process.cpu_percent()

    # Performance Report
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_duration_seconds": total_time,
        "infrastructure_status": {
            "redis_healthy": response.status_code == 200 and redis_latency < 50,
            "database_healthy": len(modules) >= 0 and db_latency < 100,
            "api_healthy": response.status_code == 200 and api_latency < 500,
        },
        "performance_metrics": {
            "redis_latency_ms": redis_latency,
            "database_latency_ms": db_latency,
            "api_latency_ms": api_latency,
        },
        "resource_usage": {"memory_usage_mb": memory_mb, "cpu_usage_percent": cpu_percent},
        "sla_compliance": {
            "redis_sla_met": redis_latency < 10.0,
            "database_sla_met": db_latency < 100.0,
            "api_sla_met": api_latency < 500.0,
        },
    }

    # All collected metrics
    all_metrics = {}
    for metric_name in metrics.measurements:
        all_metrics[metric_name] = metrics.get_stats(metric_name)

    if all_metrics:
        report["detailed_metrics"] = all_metrics

    # Overall system health
    overall_healthy = all(
        [
            report["infrastructure_status"]["redis_healthy"],
            report["infrastructure_status"]["database_healthy"],
            report["infrastructure_status"]["api_healthy"],
        ]
    )

    overall_sla_compliant = all(
        [
            report["sla_compliance"]["redis_sla_met"],
            report["sla_compliance"]["database_sla_met"],
            report["sla_compliance"]["api_sla_met"],
        ]
    )

    report["overall_status"] = {
        "system_healthy": overall_healthy,
        "sla_compliant": overall_sla_compliant,
        "production_ready": overall_healthy and overall_sla_compliant,
    }

    # Log comprehensive report
    logger.info("=== PERFORMANCE SUMMARY ===")
    logger.info(f"Redis Latency: {redis_latency:.2f}ms")
    logger.info(f"Database Latency: {db_latency:.2f}ms")
    logger.info(f"API Latency: {api_latency:.2f}ms")
    logger.info(f"Memory Usage: {memory_mb:.1f}MB")
    logger.info(f"CPU Usage: {cpu_percent:.1f}%")
    logger.info(f"System Healthy: {overall_healthy}")
    logger.info(f"SLA Compliant: {overall_sla_compliant}")
    logger.info(f"Production Ready: {report['overall_status']['production_ready']}")
    logger.info("=== END PERFORMANCE REPORT ===")

    # Production readiness assertion
    assert report["overall_status"]["production_ready"], "System not ready for production"

    return report


# Performance test markers
pytestmark = [
    pytest.mark.performance,
    pytest.mark.requires_redis,
    pytest.mark.requires_postgres,
]
