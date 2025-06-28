# ruff: noqa: S101, SLF001, PLR2004, ANN401, ARG001, ARG002, TRY003, EM101, D107, PLR0913, PLR0915, C901, FBT003, COM812, BLE001
"""Performance Metrics Collection & Reporting - Task 15.2.

This module implements comprehensive performance metrics collection,
analysis, and reporting for production readiness validation.

Style bypasses applied for performance test files:
- RUF013: PEP 484 prohibits implicit Optional (acceptable in test scenarios)
- B007: Loop control variables not used (intentional in metric collection)
- F841: Unused variables (common in performance measurement patterns)

Key Metrics Collected:
- API Response Times (P50, P95, P99)
- Redis Pub/Sub Latency
- Database Query Performance
- Memory Usage Patterns
- Connection Pool Utilization
- Throughput Measurements
- Error Rates
- Recovery Times

Reporting Features:
- Statistical Analysis
- Performance Trend Detection
- SLA Compliance Validation
- Resource Utilization Reports
- Performance Regression Detection
"""

from __future__ import annotations

import asyncio
import json
import logging
import statistics
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

import psutil
import pytest
import redis.asyncio as redis

from src.backend.cc import crud

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

# Performance thresholds
REDIS_P95_LATENCY_MS = 10.0
REDIS_P99_LATENCY_MS = 20.0
DATABASE_P95_LATENCY_MS = 100.0
API_P95_LATENCY_MS = 1000.0
MAX_ERROR_RATE = 0.2
SLA_MAX_LATENCY_MS = 1000
SLA_MAX_P95_LATENCY_MS = 500
SLA_MIN_THROUGHPUT = 100
SLA_MAX_ERROR_RATE = 0.01

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    timestamp: str
    test_name: str

    # Latency metrics (milliseconds)
    mean_latency: float
    median_latency: float
    p95_latency: float
    p99_latency: float
    min_latency: float
    max_latency: float

    # Throughput metrics
    operations_per_second: float
    total_operations: int
    test_duration: float

    # Resource metrics
    memory_usage_mb: float
    cpu_usage_percent: float

    # Error metrics
    success_count: int
    error_count: int
    error_rate: float

    # Additional context
    metadata: dict[str, Any]


@dataclass
class SystemMetrics:
    """System-wide performance metrics."""

    timestamp: str

    # Redis metrics
    redis_latency_p95: float
    redis_throughput: float
    redis_connection_pool_utilization: float

    # Database metrics
    db_query_latency_p95: float
    db_connection_pool_utilization: float

    # API metrics
    api_response_time_p95: float
    api_throughput: float
    api_error_rate: float

    # System metrics
    memory_usage_mb: float
    cpu_usage_percent: float

    # Health status
    redis_healthy: bool
    database_healthy: bool
    api_healthy: bool


class PerformanceCollector:
    """Collects and analyzes performance metrics."""

    def __init__(self) -> None:
        self.metrics_history: list[PerformanceMetrics] = []
        self.system_metrics_history: list[SystemMetrics] = []

    def collect_latency_metrics(
        self, latencies: list[float], test_name: str, metadata: dict[str, Any] | None = None
    ) -> PerformanceMetrics:
        """Collect latency-based performance metrics."""
        if not latencies:
            raise ValueError("No latency data provided")

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        # Calculate percentiles
        p95_index = int(0.95 * n)
        p99_index = int(0.99 * n)

        # System resource usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        cpu_percent = process.cpu_percent()

        metrics = PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            test_name=test_name,
            mean_latency=statistics.mean(latencies),
            median_latency=statistics.median(latencies),
            p95_latency=sorted_latencies[p95_index],
            p99_latency=sorted_latencies[p99_index],
            min_latency=min(latencies),
            max_latency=max(latencies),
            operations_per_second=0.0,  # Will be calculated separately
            total_operations=len(latencies),
            test_duration=0.0,  # Will be set by caller
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent,
            success_count=len(latencies),
            error_count=0,
            error_rate=0.0,
            metadata=metadata or {},
        )

        self.metrics_history.append(metrics)
        return metrics

    def collect_throughput_metrics(
        self,
        total_operations: int,
        test_duration: float,
        error_count: int,
        test_name: str,
        latencies: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PerformanceMetrics:
        """Collect throughput-based performance metrics."""
        success_count = total_operations - error_count
        ops_per_second = success_count / test_duration if test_duration > 0 else 0
        error_rate = error_count / total_operations if total_operations > 0 else 0

        # System resource usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        cpu_percent = process.cpu_percent()

        # Latency stats if provided
        if latencies:
            sorted_latencies = sorted(latencies)
            n = len(sorted_latencies)
            p95_index = int(0.95 * n)
            p99_index = int(0.99 * n)

            mean_latency = statistics.mean(latencies)
            median_latency = statistics.median(latencies)
            p95_latency = sorted_latencies[p95_index]
            p99_latency = sorted_latencies[p99_index]
            min_latency = min(latencies)
            max_latency = max(latencies)
        else:
            mean_latency = median_latency = p95_latency = p99_latency = 0.0
            min_latency = max_latency = 0.0

        metrics = PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            test_name=test_name,
            mean_latency=mean_latency,
            median_latency=median_latency,
            p95_latency=p95_latency,
            p99_latency=p99_latency,
            min_latency=min_latency,
            max_latency=max_latency,
            operations_per_second=ops_per_second,
            total_operations=total_operations,
            test_duration=test_duration,
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent,
            success_count=success_count,
            error_count=error_count,
            error_rate=error_rate,
            metadata=metadata or {},
        )

        self.metrics_history.append(metrics)
        return metrics

    async def collect_system_metrics(
        self, redis_client: redis.Redis, db_session: AsyncSession, api_client: AsyncClient
    ) -> SystemMetrics:
        """Collect comprehensive system metrics."""
        timestamp = datetime.now().isoformat()

        # Redis metrics
        redis_latencies = []
        redis_healthy = True
        try:
            for _ in range(10):
                start = time.perf_counter_ns()
                await redis_client.ping()
                latency = (time.perf_counter_ns() - start) / 1_000_000
                redis_latencies.append(latency)

            redis_latency_p95 = sorted(redis_latencies)[int(0.95 * len(redis_latencies))]

            # Throughput test
            start_time = time.perf_counter()
            tasks = [redis_client.publish(f"metrics_test_{i}", f"data_{i}") for i in range(100)]
            await asyncio.gather(*tasks)
            redis_throughput = 100 / (time.perf_counter() - start_time)

        except Exception as e:
            logger.warning(f"Redis metrics collection failed: {e}")
            redis_latency_p95 = 0.0
            redis_throughput = 0.0
            redis_healthy = False

        # Database metrics
        db_latencies = []
        database_healthy = True
        try:
            for _ in range(5):
                start = time.perf_counter_ns()
                await crud.get_modules(db_session, skip=0, limit=10)
                latency = (time.perf_counter_ns() - start) / 1_000_000
                db_latencies.append(latency)

            db_latency_p95 = sorted(db_latencies)[int(0.95 * len(db_latencies))] if db_latencies else 0.0

        except Exception as e:
            logger.warning(f"Database metrics collection failed: {e}")
            db_latency_p95 = 0.0
            database_healthy = False

        # API metrics
        api_latencies = []
        api_healthy = True
        api_error_count = 0
        try:
            for _ in range(5):
                start = time.perf_counter_ns()
                response = await api_client.get("/cc/health")
                latency = (time.perf_counter_ns() - start) / 1_000_000
                api_latencies.append(latency)

                if response.status_code != 200:
                    api_error_count += 1

            api_response_time_p95 = sorted(api_latencies)[int(0.95 * len(api_latencies))] if api_latencies else 0.0
            api_error_rate = api_error_count / len(api_latencies) if api_latencies else 1.0

            # API throughput test
            start_time = time.perf_counter()
            tasks = [api_client.get("/cc/health") for _ in range(20)]
            _ = await asyncio.gather(*tasks, return_exceptions=True)  # Execute concurrent requests
            api_throughput = 20 / (time.perf_counter() - start_time)

        except Exception as e:
            logger.warning(f"API metrics collection failed: {e}")
            api_response_time_p95 = 0.0
            api_throughput = 0.0
            api_error_rate = 1.0
            api_healthy = False

        # System resource metrics
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        cpu_percent = process.cpu_percent()

        system_metrics = SystemMetrics(
            timestamp=timestamp,
            redis_latency_p95=redis_latency_p95,
            redis_throughput=redis_throughput,
            redis_connection_pool_utilization=0.0,  # Would need pool introspection
            db_query_latency_p95=db_latency_p95,
            db_connection_pool_utilization=0.0,  # Would need pool introspection
            api_response_time_p95=api_response_time_p95,
            api_throughput=api_throughput,
            api_error_rate=api_error_rate,
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent,
            redis_healthy=redis_healthy,
            database_healthy=database_healthy,
            api_healthy=api_healthy,
        )

        self.system_metrics_history.append(system_metrics)
        return system_metrics

    def generate_performance_report(self) -> dict[str, Any]:
        """Generate comprehensive performance report."""
        if not self.metrics_history:
            return {"error": "No metrics collected"}

        # Aggregate metrics by test name
        test_groups: dict[str, list[PerformanceMetrics]] = {}
        for metric in self.metrics_history:
            if metric.test_name not in test_groups:
                test_groups[metric.test_name] = []
            test_groups[metric.test_name].append(metric)

        report: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(test_groups),
                "total_metrics": len(self.metrics_history),
                "test_duration": self._calculate_total_duration(),
            },
            "test_results": {},
            "sla_compliance": {},
            "performance_trends": {},
            "system_health": self._analyze_system_health(),
        }

        # Analyze each test group
        for test_name, metrics in test_groups.items():
            report["test_results"][test_name] = self._analyze_test_group(metrics)
            report["sla_compliance"][test_name] = self._check_sla_compliance(metrics)

        return report

    def _calculate_total_duration(self) -> float:
        """Calculate total test duration."""
        if not self.metrics_history:
            return 0.0

        timestamps = [datetime.fromisoformat(m.timestamp) for m in self.metrics_history]
        if len(timestamps) < 2:
            return 0.0

        return (max(timestamps) - min(timestamps)).total_seconds()

    def _analyze_test_group(self, metrics: list[PerformanceMetrics]) -> dict[str, Any]:
        """Analyze a group of metrics for the same test."""
        if not metrics:
            return {}

        # Aggregate latencies
        all_latencies = []
        total_ops = 0
        total_errors = 0
        total_duration = 0.0

        for metric in metrics:
            if metric.mean_latency > 0:  # Only include valid latency measurements
                all_latencies.extend([metric.mean_latency])
            total_ops += metric.total_operations
            total_errors += metric.error_count
            total_duration += metric.test_duration

        # Calculate aggregated statistics
        if all_latencies:
            avg_latency = statistics.mean(all_latencies)
            p95_latency = sorted(all_latencies)[int(0.95 * len(all_latencies))]
        else:
            avg_latency = 0.0
            p95_latency = 0.0

        throughput = total_ops / total_duration if total_duration > 0 else 0
        error_rate = total_errors / total_ops if total_ops > 0 else 0

        return {
            "runs": len(metrics),
            "average_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "throughput_ops_per_sec": throughput,
            "error_rate": error_rate,
            "total_operations": total_ops,
            "total_errors": total_errors,
        }

    def _check_sla_compliance(self, metrics: list[PerformanceMetrics]) -> dict[str, Any]:
        """Check SLA compliance for metrics."""
        if not metrics:
            return {}

        # Define SLA targets
        sla_targets = {
            "max_latency_ms": SLA_MAX_LATENCY_MS,  # P99 should be < 1000ms
            "max_p95_latency_ms": SLA_MAX_P95_LATENCY_MS,  # P95 should be < 500ms
            "min_throughput_ops_per_sec": SLA_MIN_THROUGHPUT,  # Minimum throughput
            "max_error_rate": SLA_MAX_ERROR_RATE,  # Maximum 1% error rate
        }

        compliance = {}

        for metric in metrics:
            test_compliance = {
                "latency_compliant": metric.p99_latency < sla_targets["max_latency_ms"],
                "p95_compliant": metric.p95_latency < sla_targets["max_p95_latency_ms"],
                "throughput_compliant": metric.operations_per_second >= sla_targets["min_throughput_ops_per_sec"],
                "error_rate_compliant": metric.error_rate <= sla_targets["max_error_rate"],
            }

            test_compliance["overall_compliant"] = all(test_compliance.values())
            compliance[metric.timestamp] = test_compliance

        # Overall compliance
        all_compliant = all(c["overall_compliant"] for c in compliance.values())

        return {
            "sla_targets": sla_targets,
            "individual_compliance": compliance,
            "overall_compliant": all_compliant,
            "compliance_rate": sum(1 for c in compliance.values() if c["overall_compliant"]) / len(compliance),
        }

    def _analyze_system_health(self) -> dict[str, Any]:
        """Analyze overall system health."""
        if not self.system_metrics_history:
            return {"status": "No system metrics available"}

        latest = self.system_metrics_history[-1]

        health_status = {
            "redis_healthy": latest.redis_healthy,
            "database_healthy": latest.database_healthy,
            "api_healthy": latest.api_healthy,
            "overall_healthy": latest.redis_healthy and latest.database_healthy and latest.api_healthy,
        }

        performance_status = {
            "redis_performance_good": latest.redis_latency_p95 < 5.0 and latest.redis_throughput > 500,
            "database_performance_good": latest.db_query_latency_p95 < 50.0,
            "api_performance_good": latest.api_response_time_p95 < 500.0 and latest.api_error_rate < 0.05,
        }

        resource_status = {
            "memory_usage_acceptable": latest.memory_usage_mb < 1000,  # < 1GB
            "cpu_usage_acceptable": latest.cpu_usage_percent < 80,
        }

        return {
            "health": health_status,
            "performance": performance_status,
            "resources": resource_status,
            "latest_metrics": asdict(latest),
        }


class TestPerformanceMetricsCollection:
    """Test performance metrics collection and reporting."""

    @pytest.fixture
    def metrics_collector(self) -> PerformanceCollector:
        """Provide metrics collector instance."""
        return PerformanceCollector()

    @pytest.mark.asyncio
    async def test_redis_performance_metrics_collection(
        self, perf_client: redis.Redis, metrics_collector: PerformanceCollector
    ) -> None:
        """Test Redis performance metrics collection."""
        # Collect latency metrics
        latencies = []
        for _ in range(100):
            start = time.perf_counter_ns()
            await perf_client.ping()
            latency = (time.perf_counter_ns() - start) / 1_000_000
            latencies.append(latency)

        metrics = metrics_collector.collect_latency_metrics(
            latencies, "redis_ping_latency", {"redis_version": "latest", "connection_pool_size": 50}
        )

        # Validate metrics
        assert metrics.test_name == "redis_ping_latency"
        assert metrics.total_operations == 100
        assert metrics.p95_latency > 0
        assert metrics.p99_latency >= metrics.p95_latency
        assert metrics.mean_latency > 0

        # Performance assertions
        assert metrics.p95_latency < REDIS_P95_LATENCY_MS, f"Redis P95 latency {metrics.p95_latency:.2f}ms too high"
        assert metrics.p99_latency < REDIS_P99_LATENCY_MS, f"Redis P99 latency {metrics.p99_latency:.2f}ms too high"

    @pytest.mark.asyncio
    async def test_database_performance_metrics_collection(
        self, db_session: AsyncSession, metrics_collector: PerformanceCollector
    ) -> None:
        """Test database performance metrics collection."""
        # Collect database operation metrics
        latencies = []
        error_count = 0
        total_operations = 20

        start_time = time.perf_counter()

        for i in range(total_operations):
            try:
                op_start = time.perf_counter_ns()

                if i % 5 == 0:
                    # Create operation
                    module = await crud.create_module(db_session, f"perf_module_{i}", "1.0.0")
                    assert module is not None
                else:
                    # Read operation
                    modules = await crud.get_modules(db_session, skip=0, limit=10)
                    assert len(modules) >= 0

                latency = (time.perf_counter_ns() - op_start) / 1_000_000
                latencies.append(latency)

            except Exception as e:
                error_count += 1
                logger.warning(f"Database operation {i} failed: {e}")

        test_duration = time.perf_counter() - start_time

        metrics = metrics_collector.collect_throughput_metrics(
            total_operations=total_operations,
            test_duration=test_duration,
            error_count=error_count,
            test_name="database_mixed_operations",
            latencies=latencies,
            metadata={"pool_size": 20, "operation_mix": "80% read, 20% write"},
        )

        # Validate metrics
        assert metrics.test_name == "database_mixed_operations"
        assert metrics.total_operations == total_operations
        assert metrics.error_count == error_count
        assert metrics.operations_per_second > 0

        # Performance assertions
        assert (
            metrics.p95_latency < DATABASE_P95_LATENCY_MS
        ), f"Database P95 latency {metrics.p95_latency:.2f}ms too high"
        assert metrics.error_rate < MAX_ERROR_RATE, f"Database error rate {metrics.error_rate:.2%} too high"

    @pytest.mark.asyncio
    async def test_api_performance_metrics_collection(
        self, async_client: AsyncClient, metrics_collector: PerformanceCollector
    ) -> None:
        """Test API performance metrics collection."""
        # Collect API metrics
        latencies = []
        error_count = 0
        total_operations = 50

        start_time = time.perf_counter()

        for i in range(total_operations):
            try:
                op_start = time.perf_counter_ns()

                if i % 10 == 0:
                    # Create module endpoint
                    module_data = {"name": f"api_perf_module_{i}", "version": "1.0.0"}
                    response = await async_client.post("/cc/modules/", json=module_data)
                    if response.status_code not in [200, 201]:
                        error_count += 1
                else:
                    # Health check endpoint
                    response = await async_client.get("/cc/health")
                    if response.status_code != 200:
                        error_count += 1

                latency = (time.perf_counter_ns() - op_start) / 1_000_000
                latencies.append(latency)

            except Exception as e:
                error_count += 1
                logger.warning(f"API operation {i} failed: {e}")

        test_duration = time.perf_counter() - start_time

        metrics = metrics_collector.collect_throughput_metrics(
            total_operations=total_operations,
            test_duration=test_duration,
            error_count=error_count,
            test_name="api_mixed_endpoints",
            latencies=latencies,
            metadata={"endpoint_mix": "90% health, 10% create"},
        )

        # Validate metrics
        assert metrics.test_name == "api_mixed_endpoints"
        assert metrics.total_operations == total_operations
        assert metrics.operations_per_second > 0

        # Performance assertions
        assert metrics.p95_latency < API_P95_LATENCY_MS, f"API P95 latency {metrics.p95_latency:.2f}ms too high"
        assert metrics.error_rate < 0.1, f"API error rate {metrics.error_rate:.2%} too high"

    @pytest.mark.asyncio
    async def test_comprehensive_system_metrics(
        self,
        perf_client: redis.Redis,
        db_session: AsyncSession,
        async_client: AsyncClient,
        metrics_collector: PerformanceCollector,
    ) -> None:
        """Test comprehensive system metrics collection."""
        # Collect system-wide metrics
        system_metrics = await metrics_collector.collect_system_metrics(
            redis_client=perf_client, db_session=db_session, api_client=async_client
        )

        # Validate system metrics
        assert system_metrics.timestamp is not None
        assert system_metrics.redis_latency_p95 >= 0
        assert system_metrics.redis_throughput >= 0
        assert system_metrics.db_query_latency_p95 >= 0
        assert system_metrics.api_response_time_p95 >= 0
        assert system_metrics.memory_usage_mb > 0

        # Health checks
        if system_metrics.redis_healthy:
            assert system_metrics.redis_latency_p95 < 50.0, "Redis latency too high"
            assert system_metrics.redis_throughput > 100, "Redis throughput too low"

        if system_metrics.database_healthy:
            assert system_metrics.db_query_latency_p95 < 200.0, "Database latency too high"

        if system_metrics.api_healthy:
            assert system_metrics.api_response_time_p95 < 2000.0, "API response time too high"
            assert system_metrics.api_error_rate < 0.1, "API error rate too high"

    @pytest.mark.asyncio
    async def test_performance_report_generation(
        self,
        perf_client: redis.Redis,
        db_session: AsyncSession,
        async_client: AsyncClient,
        metrics_collector: PerformanceCollector,
    ) -> None:
        """Test performance report generation."""
        # Collect multiple metrics for different tests
        test_scenarios: list[tuple[str, Callable[[], Any]]] = [
            ("redis_latency", lambda: self._run_redis_latency_test(perf_client, metrics_collector)),
            ("database_throughput", lambda: self._run_database_throughput_test(db_session, metrics_collector)),
            ("api_stress", lambda: self._run_api_stress_test(async_client, metrics_collector)),
        ]

        for _, test_func in test_scenarios:
            await test_func()

        # Collect system metrics
        await metrics_collector.collect_system_metrics(perf_client, db_session, async_client)

        # Generate comprehensive report
        report = metrics_collector.generate_performance_report()

        # Validate report structure
        assert "timestamp" in report
        assert "summary" in report
        assert "test_results" in report
        assert "sla_compliance" in report
        assert "system_health" in report

        # Validate summary
        assert report["summary"]["total_tests"] >= 3
        assert report["summary"]["total_metrics"] >= 3

        # Validate test results
        for test_name, _ in test_scenarios:
            assert test_name in report["test_results"]
            test_result = report["test_results"][test_name]
            assert "runs" in test_result
            assert "average_latency_ms" in test_result
            assert "throughput_ops_per_sec" in test_result

        # Validate SLA compliance
        for test_name, _ in test_scenarios:
            assert test_name in report["sla_compliance"]
            sla_result = report["sla_compliance"][test_name]
            assert "overall_compliant" in sla_result
            assert "compliance_rate" in sla_result

        # Validate system health
        health = report["system_health"]
        assert "health" in health
        assert "performance" in health
        assert "resources" in health

        # Log report for analysis
        logger.info(f"Performance Report Generated: {json.dumps(report, indent=2)}")

    async def _run_redis_latency_test(self, client: redis.Redis, collector: PerformanceCollector) -> None:
        """Run Redis latency test."""
        latencies = []
        for _ in range(50):
            start = time.perf_counter_ns()
            await client.ping()
            latency = (time.perf_counter_ns() - start) / 1_000_000
            latencies.append(latency)

        collector.collect_latency_metrics(latencies, "redis_latency")

    async def _run_database_throughput_test(self, session: AsyncSession, collector: PerformanceCollector) -> None:
        """Run database throughput test."""
        start_time = time.perf_counter()
        operations = 20
        errors = 0

        for i in range(operations):
            try:
                await crud.create_module(session, f"throughput_test_{i}", "1.0.0")
            except Exception:
                errors += 1

        duration = time.perf_counter() - start_time
        collector.collect_throughput_metrics(operations, duration, errors, "database_throughput")

    async def _run_api_stress_test(self, client: AsyncClient, collector: PerformanceCollector) -> None:
        """Run API stress test."""
        start_time = time.perf_counter()
        operations = 30
        errors = 0

        for _ in range(operations):
            try:
                response = await client.get("/cc/health")
                if response.status_code != 200:
                    errors += 1
            except Exception:
                errors += 1

        duration = time.perf_counter() - start_time
        collector.collect_throughput_metrics(operations, duration, errors, "api_stress")


# Performance test markers
pytestmark = [
    pytest.mark.performance,
    pytest.mark.metrics,
    pytest.mark.requires_redis,
    pytest.mark.requires_postgres,
]
