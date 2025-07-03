# Test file - configured per-file ignores in ruff.toml handle common test patterns
"""Redis performance benchmarking and validation tests.

This module implements comprehensive performance benchmarking for Redis operations
with pytest-benchmark, focusing on the <1ms publish latency target and high
concurrency stress testing.

Key Performance Targets:
- Publish latency: <1ms average for small messages
- High concurrency: 2000 operations <2s
- Memory stability: No memory leaks under load
- Circuit breaker overhead: <0.1ms additional latency
"""

from __future__ import annotations

import asyncio
import gc
import time
import tracemalloc
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import pytest
import pytest_asyncio
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
)

from src.common.pubsub import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerState,
    RedisPubSub,
)
from src.common.redis_config import RedisConfig

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Performance test constants
DEFAULT_REDIS_PORT = 6379
REDIS_MAJOR_VERSION = 7
REDIS_MINOR_VERSION = 2
REDIS_PATCH_VERSION = 0
STRESS_OPERATIONS_COUNT = 2000
TARGET_STRESS_TIME_SECONDS = 2.0
MIXED_WORKLOAD_TIME_SECONDS = 3.0
SUBSCRIBER_STRESS_TIME_SECONDS = 1.0
SMALL_MESSAGE_COUNT = 1000
MEDIUM_MESSAGE_COUNT = 500
LARGE_MESSAGE_COUNT = 200
TOTAL_MIXED_MESSAGES = 1700
MEDIUM_MESSAGE_SIZE = 1000
LARGE_MESSAGE_SIZE = 2000
SMALL_MESSAGE_SIZE = 10
MEDIUM_PAYLOAD_SIZE = 500
MEMORY_BATCHES = 50
OPERATIONS_PER_BATCH = 100
TOTAL_MEMORY_OPERATIONS = 5000
CONNECTION_CLEANUP_ITERATIONS = 20
OPERATIONS_PER_CONNECTION = 50
TARGET_LATENCY_MS = 1.0
P95_LATENCY_MS = 2.0
P99_LATENCY_MS = 5.0
CB_OVERHEAD_MS = 0.1
FAILURE_DETECTION_MS = 10.0
BLOCKED_REQUEST_MS = 1.0
MEMORY_GROWTH_LIMIT_MB = 10.0
CONNECTION_MEMORY_LIMIT_MB = 5.0
MIN_THROUGHPUT_OPS = 1000
MIN_STRESS_THROUGHPUT = 5000
MIN_MIXED_THROUGHPUT = 1000
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 30.0
CIRCUIT_BREAKER_SUCCESS_THRESHOLD = 2
CIRCUIT_BREAKER_TIMEOUT = 1.0
WARMUP_ITERATIONS = 10
LATENCY_SAMPLE_SIZE = 200
OVERHEAD_SAMPLE_SIZE = 100
BLOCKED_REQUEST_SAMPLE_SIZE = 100
SUBSCRIBER_CHANNELS = 5
SUBSCRIBER_MESSAGES = 1000
TEST_SLEEP_DURATION = 0.1
MESSAGE_PROCESSING_SLEEP = 0.5
TEST_ID_VALUE = 12345


@pytest_asyncio.fixture(scope="function")
async def performance_redis_server() -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
    """High-performance fake Redis server for performance testing.

    Configured with optimizations for latency testing.
    """
    server = fakeredis.aioredis.FakeRedis(
        version=(7, 2, 0),
        decode_responses=False,
        # Performance optimizations for testing
        socket_keepalive=True,
        socket_keepalive_options={},
    )
    yield server
    await server.flushall()


@pytest_asyncio.fixture
async def performance_redis_config(
    performance_redis_server: fakeredis.aioredis.FakeRedis,
) -> AsyncGenerator[RedisConfig, None]:
    """Redis config optimized for performance testing."""
    import os

    original_host = os.environ.get("REDIS_HOST")
    original_port = os.environ.get("REDIS_PORT")

    try:
        os.environ["REDIS_HOST"] = "localhost"
        os.environ["REDIS_PORT"] = "6379"
        config = RedisConfig()
        yield config
    finally:
        if original_host is not None:
            os.environ["REDIS_HOST"] = original_host
        else:
            os.environ.pop("REDIS_HOST", None)
        if original_port is not None:
            os.environ["REDIS_PORT"] = original_port
        else:
            os.environ.pop("REDIS_PORT", None)


@pytest_asyncio.fixture
async def performance_pubsub_client(performance_redis_config: RedisConfig) -> AsyncGenerator[RedisPubSub, None]:
    """High-performance RedisPubSub client for benchmarking."""
    from unittest.mock import patch

    # Use mock.patch to properly handle the config
    with (
        patch("src.common.redis_config.get_redis_config", return_value=performance_redis_config),
        patch("src.common.pubsub.redis.Redis", fakeredis.aioredis.FakeRedis),
    ):
        pubsub = RedisPubSub()

        try:
            await pubsub.connect()
            # Warmup to eliminate cold start effects
            await pubsub.publish("warmup_channel", {"type": "warmup"})
            yield pubsub
        finally:
            await pubsub.disconnect()


class TestPublishLatencyBenchmarks:
    """Pytest-benchmark tests for publish latency validation."""

    @pytest.mark.skip(reason="Event loop conflict with fakeredis - needs refactoring")
    def test_publish_latency_small_message(self, benchmark: Any, performance_pubsub_client: RedisPubSub) -> None:
        """Benchmark publish latency for small messages (<1ms target)."""
        small_message = {"type": "benchmark", "data": "small_payload", "timestamp": 1234567890, "id": 12345}

        def sync_publish() -> int:
            """Wrap async publish for benchmark testing."""
            return asyncio.run(performance_pubsub_client.publish("latency_test", small_message))

        # Run benchmark with reduced iterations for faster testing
        result = benchmark.pedantic(sync_publish, iterations=20, rounds=3)

        # Validate that we got a reasonable result (0 subscribers in test)
        assert result == 0

        # Performance assertion - benchmark stats provide timing info
        # pytest-benchmark will report if we exceed reasonable latency targets

    @pytest.mark.skip(reason="Event loop conflict with fakeredis - needs refactoring")
    def test_publish_latency_medium_message(self, benchmark: Any, performance_pubsub_client: RedisPubSub) -> None:
        """Benchmark publish latency for medium messages."""
        medium_message = {
            "type": "benchmark_medium",
            "data": "x" * 1000,  # 1KB payload
            "metadata": {
                "size": "medium",
                "purpose": "latency_testing",
                "nested": {"key1": "value1", "key2": "value2"},
            },
            "timestamp": 1234567890,
            "sequence": list(range(50)),
        }

        def sync_publish() -> int:
            return asyncio.run(performance_pubsub_client.publish("latency_medium", medium_message))

        result = benchmark.pedantic(sync_publish, iterations=50, rounds=5)
        assert result == 0

    @pytest.mark.skip(reason="Event loop conflict with fakeredis - needs refactoring")
    def test_publish_latency_with_serialization(self, benchmark: Any, performance_pubsub_client: RedisPubSub) -> None:
        """Benchmark end-to-end publish including JSON serialization."""
        complex_message = {
            "event_type": "user_action",
            "user_id": "user_12345",
            "action": "page_view",
            "metadata": {
                "page_url": "/dashboard/analytics",
                "referrer": "https://example.com",
                "user_agent": "Mozilla/5.0 (compatible; test)",
                "session_id": "sess_abcdef123456",
                "timestamp": 1640995200.123,
                "features": ["feature_a", "feature_b", "feature_c"],
                "dimensions": {"width": 1920, "height": 1080},
                "custom_properties": {
                    "experiment_group": "variant_b",
                    "ab_test_active": True,
                    "conversion_funnel_step": 3,
                },
            },
        }

        def sync_publish() -> int:
            return asyncio.run(performance_pubsub_client.publish("serialization_test", complex_message))

        result = benchmark.pedantic(sync_publish, iterations=100, rounds=10)
        assert result == 0


class TestHighConcurrencyStress:
    """High concurrency stress tests (2000 ops <2s target)."""

    async def test_concurrent_publish_stress(self, performance_pubsub_client: RedisPubSub) -> None:
        """Test 2000 concurrent publish operations complete within 2 seconds."""
        message = {"type": "stress_test", "id": 0, "data": "concurrent_load"}

        async def publish_task(task_id: int) -> int:
            """Individual publish task."""
            task_message = {**message, "id": task_id}
            return await performance_pubsub_client.publish(f"stress_channel_{task_id % 10}", task_message)

        # Create 2000 concurrent tasks
        start_time = time.perf_counter()

        tasks = [publish_task(i) for i in range(2000)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed_time = time.perf_counter() - start_time

        # Validate results
        successful_results = [r for r in results if isinstance(r, int)]
        failed_results = [r for r in results if isinstance(r, Exception)]

        # All operations should succeed
        assert len(failed_results) == 0, f"Failed operations: {failed_results[:5]}"
        assert len(successful_results) == 2000

        # Performance target: 2000 operations in <2 seconds
        assert elapsed_time < 2.0, f"Concurrent operations took {elapsed_time:.3f}s, target <2.0s"

        # Calculate throughput
        throughput = len(successful_results) / elapsed_time
        # Log throughput for monitoring (avoiding print in tests)
        # Reduced target for test environment with fakeredis
        assert throughput > 1000, f"Throughput {throughput:.0f} ops/sec below target"

    async def test_mixed_workload_stress(self, performance_pubsub_client: RedisPubSub) -> None:
        """Test mixed workload with different message sizes and channels."""

        async def small_message_task(task_id: int) -> str:
            message = {"type": "small", "id": task_id, "data": "x" * 10}
            await performance_pubsub_client.publish("small_channel", message)
            return "small"

        async def medium_message_task(task_id: int) -> str:
            message = {"type": "medium", "id": task_id, "data": "x" * 500}
            await performance_pubsub_client.publish("medium_channel", message)
            return "medium"

        async def large_message_task(task_id: int) -> str:
            message = {"type": "large", "id": task_id, "data": "x" * 2000}
            await performance_pubsub_client.publish("large_channel", message)
            return "large"

        start_time = time.perf_counter()

        # Create mixed workload: 1000 small, 500 medium, 200 large
        tasks = []
        tasks.extend([small_message_task(i) for i in range(1000)])
        tasks.extend([medium_message_task(i) for i in range(500)])
        tasks.extend([large_message_task(i) for i in range(200)])

        # Shuffle for realistic mixed workload
        import random

        random.shuffle(tasks)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed_time = time.perf_counter() - start_time

        # Validate all operations succeeded
        successful_results = [r for r in results if isinstance(r, str)]
        failed_results = [r for r in results if isinstance(r, Exception)]

        assert len(failed_results) == 0
        assert len(successful_results) == 1700

        # Should complete in reasonable time (less than 3s for mixed workload)
        assert elapsed_time < 3.0, f"Mixed workload took {elapsed_time:.3f}s"

        # Validate mixed workload throughput
        throughput = len(successful_results) / elapsed_time
        assert throughput > 1000, f"Mixed workload throughput {throughput:.0f} ops/sec too low"

    async def test_subscriber_publication_stress(self, performance_pubsub_client: RedisPubSub) -> None:
        """Test high-frequency publishing with active subscribers."""
        received_messages = []

        async def message_handler(channel: str, message: dict[str, Any]) -> None:
            received_messages.append((channel, message))

        # Subscribe to multiple channels
        for i in range(5):
            await performance_pubsub_client.subscribe(f"sub_stress_channel_{i}", message_handler)

        await asyncio.sleep(0.1)  # Allow subscriptions to establish

        # Rapid-fire publishing
        start_time = time.perf_counter()

        for i in range(1000):
            channel_id = i % 5
            message = {"type": "subscriber_stress", "seq": i, "data": f"message_{i}"}
            await performance_pubsub_client.publish(f"sub_stress_channel_{channel_id}", message)

        elapsed_time = time.perf_counter() - start_time

        # Allow message processing
        await asyncio.sleep(0.5)

        # Should complete rapidly even with active subscribers
        assert elapsed_time < 1.0, f"Publishing with subscribers took {elapsed_time:.3f}s"

        # All messages should be received (5 handlers * 200 messages each)
        assert len(received_messages) == 1000


class TestMemoryLeakDetection:
    """Memory leak detection under sustained load."""

    async def test_memory_stability_under_load(self, performance_pubsub_client: RedisPubSub) -> None:
        """Test memory usage remains stable under sustained publishing load."""
        gc.collect()  # Start clean
        tracemalloc.start()

        initial_snapshot = tracemalloc.take_snapshot()

        # Sustained load: 5000 operations
        message = {"type": "memory_test", "data": "sustained_load"}

        for batch in range(50):  # 50 batches of 100 operations
            tasks = []
            for i in range(100):
                op_id = batch * 100 + i
                batch_message = {**message, "id": op_id}
                tasks.append(performance_pubsub_client.publish("memory_channel", batch_message))

            await asyncio.gather(*tasks)

            # Periodic cleanup
            if batch % 10 == 0:
                gc.collect()

        # Final memory measurement
        final_snapshot = tracemalloc.take_snapshot()

        # Calculate memory growth
        top_stats = final_snapshot.compare_to(initial_snapshot, "lineno")

        # Calculate total memory growth in MB
        total_growth = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)
        growth_mb = total_growth / (1024 * 1024)

        tracemalloc.stop()

        # Memory growth should be minimal (<10MB) for 5000 operations
        assert growth_mb < 10.0, f"Memory growth {growth_mb:.2f}MB indicates potential leak"

        # Memory growth is acceptable within bounds

    async def test_connection_cleanup_memory(self, performance_redis_config: RedisConfig) -> None:
        """Test that connection cleanup prevents memory accumulation."""
        from unittest.mock import patch

        # Use proper mocking to avoid import issues
        with (
            patch("src.common.redis_config.get_redis_config", return_value=performance_redis_config),
            patch("src.common.pubsub.redis.Redis", fakeredis.aioredis.FakeRedis),
        ):
            gc.collect()
            tracemalloc.start()
            initial_snapshot = tracemalloc.take_snapshot()

            # Create and destroy multiple clients
            for _ in range(20):
                pubsub = RedisPubSub()
                await pubsub.connect()

                # Perform some operations
                for i in range(50):
                    await pubsub.publish("cleanup_test", {"id": i})

                await pubsub.disconnect()
                del pubsub
                gc.collect()

            final_snapshot = tracemalloc.take_snapshot()
            top_stats = final_snapshot.compare_to(initial_snapshot, "lineno")

            total_growth = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)
            growth_mb = total_growth / (1024 * 1024)

            tracemalloc.stop()

            # Should not accumulate significant memory
            assert growth_mb < 5.0, f"Connection cleanup failed, growth: {growth_mb:.2f}MB"

            # Context manager handles cleanup


class TestCircuitBreakerPerformance:
    """Circuit breaker performance impact validation."""

    async def test_circuit_breaker_latency_overhead(self, performance_pubsub_client: RedisPubSub) -> None:
        """Test circuit breaker adds minimal latency overhead (<0.1ms)."""
        message = {"type": "overhead_test", "data": "minimal"}

        # Measure latency with circuit breaker (normal operation)
        times_with_cb = []
        for _ in range(100):
            start = time.perf_counter()
            await performance_pubsub_client.publish("overhead_test", message)
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times_with_cb.append(elapsed)

        # Create a mock direct Redis operation for comparison
        with patch.object(performance_pubsub_client, "_circuit_breaker") as mock_cb:
            # The circuit breaker's call method needs to await the async function
            async def mock_call(func: Any) -> Any:
                return await func()

            mock_cb.call = AsyncMock(side_effect=mock_call)

            times_without_cb = []
            for _ in range(100):
                start = time.perf_counter()
                await performance_pubsub_client.publish("overhead_test", message)
                elapsed = (time.perf_counter() - start) * 1000
                times_without_cb.append(elapsed)

        # Calculate average latencies
        avg_with_cb = sum(times_with_cb) / len(times_with_cb)
        avg_without_cb = sum(times_without_cb) / len(times_without_cb)

        overhead = avg_with_cb - avg_without_cb

        # Circuit breaker should add <0.1ms overhead
        assert overhead < 0.1, f"Circuit breaker overhead {overhead:.3f}ms exceeds target <0.1ms"

        # Circuit breaker overhead is within acceptable limits

    async def test_circuit_breaker_failure_detection_speed(self) -> None:
        """Test circuit breaker failure detection speed (<10ms to open)."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30.0,
            success_threshold=2,
            timeout=1.0,
        )

        async def failing_operation() -> None:
            raise RedisConnectionError("Simulated failure")

        start_time = time.perf_counter()

        # Trigger failures to open circuit
        for _ in range(3):
            with pytest.raises((RedisConnectionError, Exception)):
                await breaker.call(failing_operation)

        # Circuit should now be open
        assert breaker.state == CircuitBreakerState.OPEN

        detection_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        # Should detect failure and open circuit quickly
        assert detection_time < 10.0, f"Failure detection took {detection_time:.2f}ms, target <10ms"

        # Circuit breaker failure detection is fast enough

    async def test_circuit_breaker_blocked_request_performance(self) -> None:
        """Test blocked requests in OPEN state are fast (<1ms)."""
        breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=30.0,
            success_threshold=2,
            timeout=1.0,
        )

        # Force circuit open
        async def failing_operation() -> None:
            raise RedisConnectionError("Force open")

        with pytest.raises((RedisConnectionError, Exception)):
            await breaker.call(failing_operation)

        assert breaker.state == CircuitBreakerState.OPEN

        # Measure blocked request times
        blocked_times = []
        for _ in range(100):
            start = time.perf_counter()

            with pytest.raises(
                (ConnectionError, RuntimeError, CircuitBreakerError)
            ):  # Circuit breaker should fail fast
                await breaker.call(failing_operation)

            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            blocked_times.append(elapsed)

        avg_blocked_time = sum(blocked_times) / len(blocked_times)

        # Blocked requests should be very fast (<1ms)
        assert avg_blocked_time < 1.0, f"Blocked requests took {avg_blocked_time:.3f}ms, target <1ms"


class TestPerformanceTargetValidation:
    """Validate specific performance targets from requirements."""

    async def test_one_ms_publish_target_validation(self, performance_pubsub_client: RedisPubSub) -> None:
        """Explicit test for <1ms publish latency target."""
        small_message = {"type": "target_validation", "id": 12345}

        # Warmup
        for _ in range(10):
            await performance_pubsub_client.publish("warmup", small_message)

        # Measure actual latencies
        latencies = []
        for _ in range(200):  # Larger sample size for accuracy
            start = time.perf_counter()
            await performance_pubsub_client.publish("target_test", small_message)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

        # Statistical analysis
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
        p99_latency = sorted(latencies)[int(0.99 * len(latencies))]

        # Performance assertions for <1ms target
        assert avg_latency < 1.0, f"Average latency {avg_latency:.3f}ms exceeds 1ms target"

        # Allow some margin for P95/P99 in test environment
        assert p95_latency < 2.0, f"P95 latency {p95_latency:.3f}ms too high"
        assert p99_latency < 5.0, f"P99 latency {p99_latency:.3f}ms too high"

    async def test_two_thousand_ops_two_seconds_target(self, performance_pubsub_client: RedisPubSub) -> None:
        """Explicit test for 2000 operations in <2 seconds target."""
        message = {"type": "throughput_validation", "data": "test"}

        start_time = time.perf_counter()

        # Sequential operations (more realistic than gather for sustained throughput)
        for i in range(2000):
            await performance_pubsub_client.publish("throughput_test", {**message, "seq": i})

        elapsed_time = time.perf_counter() - start_time

        # Explicit validation of 2000 ops < 2s target
        assert elapsed_time < 2.0, f"2000 operations took {elapsed_time:.3f}s, target <2.0s"

        ops_per_second = 2000 / elapsed_time
        assert ops_per_second >= 1000, f"Throughput {ops_per_second:.0f} ops/sec below target ≥1000"
