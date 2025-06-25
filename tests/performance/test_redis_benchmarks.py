"""Redis Performance Benchmarking Suite - Task 011.

This module implements comprehensive performance benchmarks for Redis operations
to validate the dual mandate requirements:

Performance Targets:
- Publish latency < 1ms
- Throughput ≥ 1000 msg/s
- Connection pool efficiency (1000 pings < 1s)
- Memory leak detection
- Regression monitoring in CI/CD

All benchmarks use pytest-benchmark for statistical validation and
automatic regression detection.
"""

from __future__ import annotations

import asyncio
import gc
import json
import time
import tracemalloc
from typing import Any

import psutil
import pytest
import redis.asyncio as redis

from .conftest import PerformanceTestUtils


class TestRedisLatencyBenchmarks:
    """Latency-focused performance benchmarks."""

    @pytest.mark.asyncio
    @pytest.mark.benchmark(group="latency", min_rounds=200)
    async def test_publish_latency_benchmark(self, benchmark: Any, perf_client: redis.Redis) -> None:
        """Benchmark publish latency with <1ms target using pytest-benchmark."""

        async def publish_operation() -> float:
            """Single publish operation with precise timing."""
            start = time.perf_counter_ns()
            await perf_client.publish("bench_latency", "test_message")
            end = time.perf_counter_ns()
            return (end - start) / 1_000_000  # Convert to milliseconds

        # Use benchmark directly for async operations
        def sync_publish() -> asyncio.Task[float]:
            return asyncio.create_task(publish_operation())

        # Run benchmark with task creation
        task = benchmark(sync_publish)
        result = await task

        # Assertion outside benchmark for clarity
        assert result < 1.0, f"Publish latency {result:.3f}ms exceeds 1ms target"

    @pytest.mark.asyncio
    async def test_latency_percentiles_validation(
        self, perf_client: redis.Redis, perf_utils: PerformanceTestUtils
    ) -> None:
        """Validate latency distribution meets SLA requirements."""
        latencies = []

        # Warmup
        for _ in range(100):
            await perf_client.publish("warmup", "data")

        # Measure latency distribution
        for _ in range(10000):
            start = time.perf_counter_ns()
            await perf_client.publish("perf_test", "data")
            end = time.perf_counter_ns()
            latencies.append((end - start) / 1_000_000)

        stats = perf_utils.calculate_percentiles(latencies)

        # SLA validation
        assert stats["mean"] < 1.0, f"Mean latency {stats['mean']:.3f}ms exceeds 1ms"
        assert stats["p95"] < 2.0, f"P95 latency {stats['p95']:.3f}ms exceeds 2ms"
        assert stats["p99"] < 5.0, f"P99 latency {stats['p99']:.3f}ms exceeds 5ms"


class TestRedisThroughputBenchmarks:
    """Throughput-focused performance benchmarks."""

    @pytest.mark.asyncio
    @pytest.mark.benchmark(group="throughput", min_rounds=50, max_time=5.0)
    async def test_throughput_stress_benchmark(self, benchmark: Any, perf_client: redis.Redis) -> None:
        """Benchmark sustained throughput with ≥1000 msg/s target."""

        async def throughput_test() -> float:
            """Measure messages per second throughput."""
            start_time = time.perf_counter()

            # Concurrent batch publishing for realistic load
            tasks = []
            for i in range(1000):
                task = perf_client.publish(f"stress_{i % 10}", f"message_{i}")
                tasks.append(task)

            await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start_time
            return 1000 / elapsed  # Messages per second

        result = benchmark(lambda: asyncio.run(throughput_test()))
        assert result >= 1000, f"Throughput {result:.0f} msg/s below 1000 msg/s target"

    @pytest.mark.asyncio
    async def test_sustained_load_validation(self, perf_client: redis.Redis) -> None:
        """Test sustained load over extended duration."""
        duration = 10  # seconds
        start_time = time.perf_counter()
        message_count = 0

        while time.perf_counter() - start_time < duration:
            # Batch operations for efficiency
            batch_tasks = []
            for i in range(100):
                task = perf_client.publish("sustained_load", f"msg_{message_count + i}")
                batch_tasks.append(task)

            await asyncio.gather(*batch_tasks)
            message_count += 100

        actual_duration = time.perf_counter() - start_time
        throughput = message_count / actual_duration

        assert throughput >= 1000, f"Sustained throughput {throughput:.0f} msg/s insufficient"

    @pytest.mark.asyncio
    @pytest.mark.benchmark(group="concurrent", min_rounds=20, max_time=3.0)
    async def test_concurrent_throughput_benchmark(self, benchmark: Any, perf_client: redis.Redis) -> None:
        """Benchmark concurrent client throughput."""

        async def concurrent_test() -> float:
            """Test multiple concurrent publishers."""

            async def publisher_task(client_id: int) -> int:
                count = 0
                for i in range(100):
                    await perf_client.publish(f"concurrent_{client_id}", f"msg_{i}")
                    count += 1
                return count

            start_time = time.perf_counter()

            # 10 concurrent publishers, 100 messages each
            tasks = [publisher_task(i) for i in range(10)]
            results = await asyncio.gather(*tasks)

            elapsed = time.perf_counter() - start_time
            total_messages = sum(results)
            return total_messages / elapsed

        result = benchmark(lambda: asyncio.run(concurrent_test()))
        assert result >= 1000, f"Concurrent throughput {result:.0f} msg/s insufficient"


class TestConnectionPoolBenchmarks:
    """Connection pool efficiency benchmarks."""

    @pytest.mark.asyncio
    @pytest.mark.benchmark(group="pool_efficiency", min_rounds=100, warmup_rounds=20)
    async def test_connection_pool_efficiency_benchmark(
        self, benchmark: Any, perf_clients_from_pool: list[redis.Redis]
    ) -> None:
        """Benchmark connection pool efficiency - 1000 pings < 1s target."""

        async def pool_operations() -> float:
            """Test connection pool reuse efficiency."""
            start = time.perf_counter()

            # 1000 ping operations across multiple clients
            tasks = []
            for _ in range(1000):
                client = perf_clients_from_pool[_ % len(perf_clients_from_pool)]
                task = client.ping()
                tasks.append(task)

            await asyncio.gather(*tasks)
            return time.perf_counter() - start

        result = benchmark(lambda: asyncio.run(pool_operations()))
        assert result < 1.0, f"1000 ping operations took {result:.3f}s, target <1.0s"

    @pytest.mark.asyncio
    async def test_pool_vs_individual_connections(self, perf_client_pool: redis.ConnectionPool) -> None:
        """Compare pooled vs individual connection performance."""
        # Test with shared pool
        pooled_client = redis.Redis(connection_pool=perf_client_pool)

        start = time.perf_counter()
        for _ in range(1000):
            await pooled_client.ping()
        pooled_time = time.perf_counter() - start

        await pooled_client.aclose()

        # Test individual connections
        start = time.perf_counter()
        for _ in range(1000):
            client = redis.Redis(host="localhost", port=6379)
            await client.ping()
            await client.aclose()
        individual_time = time.perf_counter() - start

        efficiency_gain = (individual_time - pooled_time) / individual_time
        assert efficiency_gain > 0.5, f"Pool efficiency gain {efficiency_gain:.2%} too low"

    @pytest.mark.asyncio
    async def test_pool_connection_reuse(self, perf_client_pool: redis.ConnectionPool) -> None:
        """Validate connection pool properly reuses connections."""
        clients = []

        # Create multiple clients from same pool
        for _ in range(20):
            client = redis.Redis(connection_pool=perf_client_pool)
            clients.append(client)

        # All should use same underlying connections
        tasks = []
        for client in clients:
            for _ in range(50):
                task = client.ping()
                tasks.append(task)

        start = time.perf_counter()
        await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        # Should be efficient due to connection reuse
        assert elapsed < 2.0, f"Pool reuse test took {elapsed:.3f}s, efficiency concern"

        # Cleanup
        for client in clients:
            await client.aclose()


class TestMemoryLeakDetection:
    """Memory leak detection and monitoring."""

    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, perf_client: redis.Redis) -> None:
        """Detect memory leaks during extended Redis operations."""
        process = psutil.Process()

        # Baseline memory measurement
        gc.collect()
        baseline_memory = process.memory_info().rss

        # Extended operation cycles
        for cycle in range(100):
            tasks = []
            for i in range(100):
                task = perf_client.publish("memory_test", f"data_{cycle}_{i}" * 10)
                tasks.append(task)

            await asyncio.gather(*tasks)

            # Periodic memory check
            if cycle % 20 == 0:
                gc.collect()
                current_memory = process.memory_info().rss
                memory_growth = (current_memory - baseline_memory) / (1024 * 1024)  # MB

                assert memory_growth < 100, f"Memory growth {memory_growth:.1f}MB at cycle {cycle}"

    @pytest.mark.asyncio
    async def test_tracemalloc_leak_detection(self, perf_client: redis.Redis) -> None:
        """Use tracemalloc for detailed memory leak detection."""
        gc.collect()
        tracemalloc.start()

        initial_snapshot = tracemalloc.take_snapshot()

        # Sustained operations
        for batch in range(50):
            for i in range(200):
                message_data = {"id": batch * 200 + i, "data": "x" * 100}
                await perf_client.publish("tracemalloc_test", json.dumps(message_data))

            # Periodic cleanup
            if batch % 10 == 0:
                gc.collect()

        final_snapshot = tracemalloc.take_snapshot()
        top_stats = final_snapshot.compare_to(initial_snapshot, "lineno")

        total_growth = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)
        growth_mb = total_growth / (1024 * 1024)

        tracemalloc.stop()

        assert growth_mb < 50.0, f"Memory growth {growth_mb:.2f}MB excessive for operations"

    @pytest.mark.asyncio
    async def test_connection_pool_memory_hygiene(self, perf_client_pool: redis.ConnectionPool) -> None:
        """Test connection pool doesn't leak connections or memory."""
        initial_connections = len(perf_client_pool._available_connections)
        initial_in_use = len(perf_client_pool._in_use_connections)

        # Create and release many clients
        for _ in range(20):
            clients = []
            for _ in range(10):
                client = redis.Redis(connection_pool=perf_client_pool)
                clients.append(client)

            # Use clients
            tasks = []
            for client in clients:
                for _ in range(10):
                    task = client.ping()
                    tasks.append(task)
            await asyncio.gather(*tasks)

            # Cleanup clients
            for client in clients:
                await client.aclose()

        # Verify no connection leaks
        final_connections = len(perf_client_pool._available_connections)
        final_in_use = len(perf_client_pool._in_use_connections)

        assert final_in_use == initial_in_use, f"Connection leak: {final_in_use} in use"
        assert final_connections >= initial_connections, "Connection pool degraded"


class TestRegressionDetection:
    """Performance regression detection tests."""

    @pytest.mark.asyncio
    @pytest.mark.benchmark(group="regression_baseline", min_rounds=100, max_time=3.0, warmup_rounds=20)
    async def test_publish_baseline_benchmark(self, benchmark: Any, perf_client: redis.Redis) -> None:
        """Baseline benchmark for regression detection in CI."""

        async def baseline_publish() -> None:
            """Execute the standard publish operation for baseline measurement."""
            await perf_client.publish("baseline_test", "standard_payload")

        benchmark(lambda: asyncio.run(baseline_publish()))

    @pytest.mark.asyncio
    @pytest.mark.benchmark(group="regression_throughput", min_rounds=20, max_time=2.0)
    async def test_throughput_baseline_benchmark(self, benchmark: Any, perf_client: redis.Redis) -> None:
        """Throughput baseline for regression detection."""

        async def baseline_throughput() -> None:
            """Execute the standard throughput test for regression monitoring."""
            tasks = []
            for i in range(500):
                task = perf_client.publish(f"throughput_baseline_{i % 5}", f"msg_{i}")
                tasks.append(task)
            await asyncio.gather(*tasks)

        benchmark(lambda: asyncio.run(baseline_throughput()))

    @pytest.mark.asyncio
    async def test_performance_targets_validation(self, perf_client: redis.Redis) -> None:
        """Comprehensive validation of all performance targets."""
        # Target 1: Latency validation
        latencies = []
        for _ in range(1000):
            start = time.perf_counter_ns()
            await perf_client.publish("validation_test", "latency_data")
            end = time.perf_counter_ns()
            latencies.append((end - start) / 1_000_000)

        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]

        # Target 2: Throughput validation
        start_time = time.perf_counter()
        tasks = []
        for i in range(2000):
            task = perf_client.publish("validation_throughput", f"msg_{i}")
            tasks.append(task)
        await asyncio.gather(*tasks)
        throughput_time = time.perf_counter() - start_time
        throughput = 2000 / throughput_time

        # Target 3: Pool efficiency validation
        start_time = time.perf_counter()
        ping_tasks = [perf_client.ping() for _ in range(1000)]
        await asyncio.gather(*ping_tasks)
        ping_time = time.perf_counter() - start_time

        # Assert all targets met
        assert avg_latency < 1.0, f"Average latency {avg_latency:.3f}ms exceeds 1ms"
        assert p95_latency < 2.0, f"P95 latency {p95_latency:.3f}ms exceeds 2ms"
        assert throughput >= 1000, f"Throughput {throughput:.0f} msg/s below 1000"
        assert ping_time < 1.0, f"1000 pings took {ping_time:.3f}s, target <1.0s"


# Performance test markers for CI filtering
pytestmark = [
    pytest.mark.performance,
    pytest.mark.requires_redis,
]
