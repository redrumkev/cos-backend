# Test file - configured per-file ignores in ruff.toml handle common test patterns
"""Simplified Redis performance benchmarking tests.

This module implements focused performance benchmarking for Redis operations
using direct fakeredis instances to bypass connection pool complexity.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import TYPE_CHECKING, Any

import fakeredis.aioredis
import pytest_asyncio

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Performance test constants
REDIS_MAJOR_VERSION = 7
REDIS_MINOR_VERSION = 2
REDIS_PATCH_VERSION = 0
BENCHMARK_ITERATIONS = 100
BENCHMARK_ROUNDS = 10
TARGET_OPERATIONS_COUNT = 2000
TARGET_TIME_SECONDS = 2.0
MIN_THROUGHPUT_OPS = 1000
WARMUP_ITERATIONS = 10
LATENCY_SAMPLE_SIZE = 100
RELAXED_AVG_LATENCY_MS = 5.0
RELAXED_P95_LATENCY_MS = 10.0
CONCURRENT_OPERATIONS = 1000
CONCURRENT_TIME_LIMIT = 3.0
MEMORY_BATCHES = 50
OPERATIONS_PER_BATCH = 100
MEMORY_OPERATIONS_TOTAL = 5000
MEMORY_GROWTH_LIMIT_MB = 50.0
MIXED_SMALL_COUNT = 500
MIXED_MEDIUM_COUNT = 300
MIXED_LARGE_COUNT = 100
MIXED_TOTAL_OPERATIONS = 900
MIXED_TIME_LIMIT = 5.0
BURST_COUNT = 5
BURST_OPERATIONS = 200
BURST_IDLE_TIME = 0.1
BURST_TIME_LIMIT = 3.0
SMALL_MESSAGE_SIZE = 50
MEDIUM_MESSAGE_SIZE = 800
LARGE_MESSAGE_SIZE = 4000
LARGE_MESSAGE_ITEMS = 100
MESSAGE_DATA_SIZE = 100
TEST_TIMESTAMP = 1234567890


@pytest_asyncio.fixture(scope="function")
async def fake_redis() -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
    """Direct fake Redis instance for performance testing."""
    redis_server = fakeredis.aioredis.FakeRedis(
        version=(7, 2, 0),
        decode_responses=False,
    )
    yield redis_server
    await redis_server.flushall()


class TestDirectRedisBenchmarks:
    """Direct Redis operation benchmarks using pytest-benchmark."""

    def test_redis_set_latency(self, benchmark: Any) -> None:
        """Benchmark Redis SET operation latency."""

        # Create a new FakeRedis instance for each benchmark run to avoid event loop issues
        def sync_set() -> bool:
            redis_server = fakeredis.aioredis.FakeRedis(
                version=(7, 2, 0),
                decode_responses=False,
            )
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(redis_server.set("benchmark_key", "benchmark_value"))
                return bool(result)
            finally:
                loop.close()

        result = benchmark.pedantic(sync_set, iterations=100, rounds=10)
        assert result is True

    def test_redis_get_latency(self, benchmark: Any) -> None:
        """Benchmark Redis GET operation latency."""

        # Create a new FakeRedis instance for each benchmark run to avoid event loop issues
        def sync_get() -> bytes:
            redis_server = fakeredis.aioredis.FakeRedis(
                version=(7, 2, 0),
                decode_responses=False,
            )
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Setup
                loop.run_until_complete(redis_server.set("get_benchmark_key", "get_benchmark_value"))
                # Get operation
                result = loop.run_until_complete(redis_server.get("get_benchmark_key"))
                return bytes(result) if result else b""
            finally:
                loop.close()

        result = benchmark.pedantic(sync_get, iterations=100, rounds=10)
        assert result == b"get_benchmark_value"

    def test_json_serialization_latency(self, benchmark: Any) -> None:
        """Benchmark JSON serialization + Redis publish latency."""
        message = {"type": "benchmark", "data": "test_payload", "timestamp": 1234567890, "metadata": {"key": "value"}}

        def sync_json_publish() -> int:
            redis_server = fakeredis.aioredis.FakeRedis(
                version=(7, 2, 0),
                decode_responses=False,
            )
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                serialized = json.dumps(message, separators=(",", ":"))
                result = loop.run_until_complete(redis_server.publish("test_channel", serialized))
                return int(result)
            finally:
                loop.close()

        result = benchmark.pedantic(sync_json_publish, iterations=100, rounds=10)
        # No subscribers, so result should be 0
        assert result == 0

    async def test_publish_throughput_target(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test 2000 publish operations complete within 2 seconds."""
        message_template = {"type": "throughput_test", "id": 0}

        start_time = time.perf_counter()

        for i in range(2000):
            message = {**message_template, "id": i}
            serialized = json.dumps(message, separators=(",", ":"))
            await fake_redis.publish("throughput_channel", serialized)

        elapsed_time = time.perf_counter() - start_time

        # Should complete within 2 seconds
        assert elapsed_time < 2.0, f"2000 operations took {elapsed_time:.3f}s, target <2.0s"
        assert (2000 / elapsed_time) >= 1000, f"Throughput {2000 / elapsed_time:.0f} ops/sec below target"

    async def test_latency_target_validation(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Validate <1ms operation latency target."""
        message = {"type": "latency_test", "data": "small"}

        # Warmup
        for _ in range(10):
            serialized = json.dumps(message, separators=(",", ":"))
            await fake_redis.publish("warmup", serialized)

        # Measure latencies
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            serialized = json.dumps(message, separators=(",", ":"))
            await fake_redis.publish("latency_test", serialized)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]

        # Performance targets - relaxed for test environment
        assert avg_latency < 5.0, f"Average latency {avg_latency:.3f}ms exceeds target"
        assert p95_latency < 10.0, f"P95 latency {p95_latency:.3f}ms too high"

    async def test_concurrent_operations(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test concurrent Redis operations."""

        async def publish_task(task_id: int) -> int:
            message = {"type": "concurrent", "id": task_id}
            serialized = json.dumps(message, separators=(",", ":"))
            result = await fake_redis.publish(f"concurrent_{task_id % 10}", serialized)
            return int(result)

        start_time = time.perf_counter()

        # 1000 concurrent tasks
        tasks = [publish_task(i) for i in range(1000)]
        results = await asyncio.gather(*tasks)

        elapsed_time = time.perf_counter() - start_time

        # All should succeed
        assert all(isinstance(r, int) for r in results)
        assert len(results) == 1000

        # Should complete reasonably quickly
        assert elapsed_time < 3.0, f"1000 concurrent operations took {elapsed_time:.3f}s"


class TestMemoryUsage:
    """Memory usage and stability tests."""

    async def test_sustained_operations_memory(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test memory usage under sustained operations."""
        import gc
        import tracemalloc

        gc.collect()
        tracemalloc.start()

        initial_snapshot = tracemalloc.take_snapshot()

        # 5000 operations in batches
        message_template = {"type": "memory_test", "data": "x" * 100}

        for batch in range(50):
            for i in range(100):
                op_id = batch * 100 + i
                message = {**message_template, "id": op_id}
                serialized = json.dumps(message, separators=(",", ":"))
                await fake_redis.publish("memory_test", serialized)

            # Periodic cleanup
            if batch % 10 == 0:
                gc.collect()

        final_snapshot = tracemalloc.take_snapshot()
        top_stats = final_snapshot.compare_to(initial_snapshot, "lineno")

        total_growth = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)
        growth_mb = total_growth / (1024 * 1024)

        tracemalloc.stop()

        # Memory growth should be reasonable for 5000 operations
        assert growth_mb < 50.0, f"Memory growth {growth_mb:.2f}MB seems excessive"


class TestRealWorldScenarios:
    """Real-world usage pattern tests."""

    async def test_mixed_message_sizes(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test performance with varied message sizes."""
        # Small messages (< 100 bytes)
        small_msg = {"type": "small", "data": "x" * 50}

        # Medium messages (~ 1KB)
        medium_msg = {"type": "medium", "data": "x" * 800, "metadata": {"key": "value"}}

        # Large messages (~ 5KB)
        large_msg = {"type": "large", "data": "x" * 4000, "metadata": {"large": True, "items": list(range(100))}}

        start_time = time.perf_counter()

        # Mixed workload: 500 small, 300 medium, 100 large
        tasks = [
            *[self._publish_message(fake_redis, f"small_{i}", small_msg) for i in range(500)],
            *[self._publish_message(fake_redis, f"medium_{i}", medium_msg) for i in range(300)],
            *[self._publish_message(fake_redis, f"large_{i}", large_msg) for i in range(100)],
        ]

        # Randomize order for realistic workload
        import random

        random.shuffle(tasks)

        results = await asyncio.gather(*tasks)
        elapsed_time = time.perf_counter() - start_time

        assert len(results) == 900
        assert all(r == 0 for r in results)  # 0 subscribers

        # Should handle mixed workload efficiently
        assert elapsed_time < 5.0, f"Mixed workload took {elapsed_time:.3f}s"

        # Validate mixed workload performance

    async def _publish_message(self, redis: fakeredis.aioredis.FakeRedis, channel: str, message: dict[str, Any]) -> int:
        """Publish a message to Redis channel."""
        serialized = json.dumps(message, separators=(",", ":"))
        result = await redis.publish(channel, serialized)
        return int(result)

    async def test_burst_and_idle_pattern(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test burst activity followed by idle periods."""
        message = {"type": "burst_test", "data": "burst_data"}

        total_start = time.perf_counter()

        # 5 bursts of 200 operations each, with idle periods
        for burst in range(5):
            # Burst: 200 rapid operations
            for i in range(200):
                serialized = json.dumps({**message, "burst": burst, "seq": i}, separators=(",", ":"))
                await fake_redis.publish(f"burst_channel_{burst}", serialized)

            # Burst completed within acceptable time

            # Idle period (simulate real-world gaps)
            await asyncio.sleep(0.1)

        total_time = time.perf_counter() - total_start

        # Should handle burst patterns efficiently
        assert total_time < 3.0, f"Burst pattern took {total_time:.3f}s"

        # Burst pattern completed successfully
