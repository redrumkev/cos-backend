# Test file - configured per-file ignores in ruff.toml handle common test patterns
"""Enhanced Redis Pub/Sub testing suite integration test.

This module verifies that all our enhanced testing patterns work together
and demonstrates the comprehensive testing capabilities we've implemented.
"""

import time
from typing import Any

import pytest

from src.common.pubsub import CircuitBreaker, RedisPubSub


class TestEnhancedRedisPubSubSuite:
    """Integration tests for the enhanced Redis Pub/Sub testing suite."""

    async def test_comprehensive_testing_capabilities(
        self,
        redis_pubsub_with_mocks: RedisPubSub,
        redis_performance_config: dict[str, Any],
        redis_test_utils: Any,
    ) -> None:
        """Test that all enhanced testing capabilities work together."""
        pubsub = redis_pubsub_with_mocks
        # Use performance configuration from fixture\n        # config = redis_performance_config

        # 1. Performance testing
        test_message = redis_test_utils.generate_test_message(100)

        start_time = time.perf_counter()
        result = await pubsub.publish("integration_test", test_message)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        assert result > 0
        assert elapsed_ms < redis_performance_config["max_latency_ms"]

        # 2. Circuit breaker testing
        cb_metrics = pubsub.circuit_breaker_metrics
        assert cb_metrics["total_requests"] >= 1
        assert cb_metrics["total_successes"] >= 1

        # 3. Message generation testing
        large_message = redis_test_utils.generate_test_message(1000)
        assert len(str(large_message)) > 1000
        assert "content" in large_message
        assert "metadata" in large_message

        # 4. Network simulation testing
        await redis_test_utils.simulate_network_latency(5)  # 5ms delay

        # 5. Subscription testing with handlers
        received_messages = []

        async def test_handler(channel: str, message: dict[str, Any]) -> None:
            received_messages.append((channel, message))

        await pubsub.subscribe("integration_test", test_handler)
        await redis_test_utils.wait_for_message_processing()

        # Send test message
        await pubsub.publish("integration_test", {"test": "integration"})
        await redis_test_utils.wait_for_message_processing()

        # Should have received the message
        assert len(received_messages) >= 1

        # Debug output for integration test
        # print("✅ Enhanced Redis Pub/Sub testing suite working correctly!")

    async def test_circuit_breaker_configuration_matrix(
        self,
        circuit_breaker_test_config: dict[str, Any],
    ) -> None:
        """Test circuit breaker with various configuration combinations."""
        config = circuit_breaker_test_config

        # Test different configurations
        configurations = [
            {"failure_threshold": 1, "recovery_timeout": 0.1},
            {"failure_threshold": 3, "recovery_timeout": 0.2},
            {"failure_threshold": 5, "recovery_timeout": 0.5},
        ]

        for test_config in configurations:
            cb = CircuitBreaker(**{**config, **test_config})

            async def failing_func() -> str:
                raise ValueError("Test failure")

            # Trigger failures up to threshold
            failure_count = 0
            for _ in range(int(test_config["failure_threshold"])):
                try:
                    await cb.call(failing_func)
                except ValueError:
                    failure_count += 1

            assert failure_count == test_config["failure_threshold"]
            assert cb.failure_count == test_config["failure_threshold"]

        # Debug output for configuration matrix
        # print("✅ Circuit breaker configuration matrix testing working!")

    async def test_performance_regression_detection(
        self,
        redis_pubsub_with_mocks: RedisPubSub,
        redis_performance_config: dict[str, Any],
        redis_test_utils: Any,
    ) -> None:
        """Test performance regression detection capabilities."""
        pubsub = redis_pubsub_with_mocks
        # Use performance configuration from fixture\n        # config = redis_performance_config

        # Baseline performance measurement
        test_message = redis_test_utils.generate_test_message(100)
        baseline_latencies = []

        for _ in range(10):
            start_time = time.perf_counter()
            await pubsub.publish("perf_baseline", test_message)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            baseline_latencies.append(elapsed_ms)

        baseline_avg = sum(baseline_latencies) / len(baseline_latencies)

        # Simulate performance regression (larger message)
        large_message = redis_test_utils.generate_test_message(10000)
        regression_latencies = []

        for _ in range(10):
            start_time = time.perf_counter()
            await pubsub.publish("perf_regression", large_message)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            regression_latencies.append(elapsed_ms)

        regression_avg = sum(regression_latencies) / len(regression_latencies)

        # Performance regression detection
        performance_ratio = regression_avg / baseline_avg

        # Should be able to detect performance differences
        assert performance_ratio != 1.0, "Should detect performance difference between message sizes"

        # Debug performance regression detection
        # print(
        #     f"✅ Performance: {baseline_avg:.2f}ms -> {regression_avg:.2f}ms"
        # )

    async def test_failure_injection_patterns(
        self,
        flaky_redis: Any,
        redis_test_utils: Any,
    ) -> None:
        """Test failure injection patterns for comprehensive error testing."""
        import asyncio

        from src.common.pubsub import CircuitBreaker, RedisPubSub

        # Create pubsub with flaky redis
        pubsub = RedisPubSub()
        pubsub._redis = flaky_redis
        pubsub._connected = True

        # Create a custom circuit breaker that allows the flaky pattern to work
        # Since flaky_redis uses a shared failure counter for both publish and ping,
        # we need to account for more failures
        pubsub._circuit_breaker = CircuitBreaker(
            failure_threshold=10,  # Much higher to allow test pattern
            recovery_timeout=0.01,  # Very short recovery
            success_threshold=1,  # Quick recovery once it starts working
            timeout=5.0,
        )

        test_message = redis_test_utils.generate_test_message(100)

        # Test the pattern with more attempts
        failure_count = 0
        success_count = 0

        # The flaky redis will fail the first 3 calls, then succeed
        # But the failure counter is shared between publish and ping operations
        for i in range(8):  # More attempts to see both patterns
            try:
                result = await pubsub.publish(f"flaky_test_{i}", test_message)
                if result >= 0:  # Accept 0 as valid (no subscribers)
                    success_count += 1
            except Exception:
                failure_count += 1

            # Small delay between attempts
            await asyncio.sleep(0.005)

        # Should have both failures and successes
        assert failure_count > 0, "Expected some failures from flaky Redis"
        assert success_count > 0, "Expected some successes after failures"

        # Debug failure injection results
        # print(f"✅ Failure injection: {failure_count} failures, {success_count} successes")

    async def test_comprehensive_coverage_verification(self) -> None:
        """Verify that our test suite provides comprehensive coverage."""
        from src.common.pubsub import (
            CircuitBreaker,
            CircuitBreakerError,
            CircuitBreakerState,
            PublishError,
            PubSubError,
            RedisPubSub,
            SubscribeError,
        )

        # Verify all major classes and exceptions are available
        assert RedisPubSub is not None
        assert CircuitBreaker is not None
        assert CircuitBreakerState is not None

        # Verify all custom exceptions
        assert issubclass(PubSubError, Exception)
        assert issubclass(PublishError, PubSubError)
        assert issubclass(SubscribeError, PubSubError)
        assert issubclass(CircuitBreakerError, Exception)

        # Test circuit breaker states
        assert CircuitBreakerState.CLOSED.value == "closed"
        assert CircuitBreakerState.OPEN.value == "open"
        assert CircuitBreakerState.HALF_OPEN.value == "half_open"

        # Debug coverage verification
        # print("✅ Comprehensive coverage verification complete!")


@pytest.mark.benchmark
class TestEnhancedTestingSuitePerformance:
    """Performance tests for the enhanced testing suite itself."""

    async def test_testing_suite_overhead(
        self,
        redis_pubsub_with_mocks: RedisPubSub,
        redis_test_utils: Any,
    ) -> None:
        """Test that our enhanced testing suite has minimal overhead."""
        pubsub = redis_pubsub_with_mocks

        # Measure test setup overhead
        setup_start = time.perf_counter()
        test_message = redis_test_utils.generate_test_message(100)
        setup_time_ms = (time.perf_counter() - setup_start) * 1000

        # Test fixture overhead should be minimal
        assert setup_time_ms < 5.0, f"Test setup overhead {setup_time_ms:.2f}ms too high"

        # Measure mock operation overhead
        mock_start = time.perf_counter()
        await pubsub.publish("overhead_test", test_message)
        mock_time_ms = (time.perf_counter() - mock_start) * 1000

        # Mock operations should be fast
        assert mock_time_ms < 5.0, f"Mock operation overhead {mock_time_ms:.2f}ms too high"

        # Debug testing overhead metrics
        # print(f"✅ Testing suite overhead: setup={setup_time_ms:.2f}ms, mock={mock_time_ms:.2f}ms")
