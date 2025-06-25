# ruff: noqa: S106  # Hardcoded passwords acceptable in test fixtures
"""Shared fixtures for performance testing."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
import redis.asyncio as redis

# Reuse Redis configuration from main conftest


@pytest_asyncio.fixture(scope="function")
async def redis_url() -> str:
    """Redis URL for performance testing."""
    return "redis://localhost:6379/0"


@pytest_asyncio.fixture(scope="function")
async def perf_client(redis_url: str) -> AsyncGenerator[redis.Redis, None]:
    """High-performance Redis client optimized for benchmarking."""
    client = redis.from_url(
        redis_url,
        password="Police9119!!Red",  # Redis auth password
        max_connections=50,  # Higher pool for stress testing
        encoding="utf-8",
        decode_responses=True,
        protocol=2,  # RESP2 for compatibility
        socket_keepalive=True,
        socket_keepalive_options={},
        retry_on_timeout=True,
        health_check_interval=30,
    )
    try:
        yield client
    finally:
        await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def perf_client_pool() -> AsyncGenerator[redis.ConnectionPool, None]:
    """Dedicated connection pool for efficiency testing."""
    pool = redis.ConnectionPool.from_url(
        "redis://localhost:6379/0",
        password="Police9119!!Red",  # Redis auth password
        max_connections=50,
        retry_on_timeout=True,
        socket_keepalive=True,
        socket_keepalive_options={},
    )
    try:
        yield pool
    finally:
        await pool.aclose()


@pytest_asyncio.fixture(scope="function")
async def perf_clients_from_pool(perf_client_pool: redis.ConnectionPool) -> AsyncGenerator[list[redis.Redis], None]:
    """Multiple Redis clients sharing the same connection pool."""
    clients = []
    for _ in range(10):
        client = redis.Redis(
            connection_pool=perf_client_pool,
            decode_responses=True,
        )
        clients.append(client)

    try:
        yield clients
    finally:
        for client in clients:
            await client.aclose()


@pytest.fixture
def benchmark_config() -> dict[str, Any]:
    """Provide configuration for pytest-benchmark."""
    return {
        "min_rounds": 200,
        "max_time": 2.0,
        "warmup_rounds": 50,
        "disable_gc": True,
        "timer": "time.perf_counter",
    }


class PerformanceTestUtils:
    """Utilities for performance testing."""

    @staticmethod
    def calculate_percentiles(latencies: list[float]) -> dict[str, float]:
        """Calculate performance percentiles."""
        import statistics

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        return {
            "mean": statistics.mean(sorted_latencies),
            "median": statistics.median(sorted_latencies),
            "p95": sorted_latencies[int(0.95 * n)],
            "p99": sorted_latencies[int(0.99 * n)],
            "min": min(sorted_latencies),
            "max": max(sorted_latencies),
        }


@pytest.fixture
def perf_utils() -> PerformanceTestUtils:
    """Provide performance testing utilities."""
    return PerformanceTestUtils()
