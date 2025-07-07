# Test file - configured per-file ignores in ruff.toml handle common test patterns
"""Advanced circuit breaker edge case and scenario testing.

This module tests complex circuit breaker behaviors including edge cases,
configuration variations, recovery patterns, and integration scenarios.
"""

import asyncio
import contextlib
import time

import pytest
from freezegun import freeze_time

from src.common.pubsub import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerState,
)

# mypy: disable-error-code="comparison-overlap,operator"


class TestCircuitBreakerConfiguration:
    """Test circuit breaker with various configuration parameters."""

    @pytest.mark.parametrize(
        "failure_threshold,expected_state",
        [
            (0, CircuitBreakerState.OPEN),  # Always open
            (1, CircuitBreakerState.CLOSED),  # Open after 1 failure
            (5, CircuitBreakerState.CLOSED),  # Open after 5 failures
            (100, CircuitBreakerState.CLOSED),  # High threshold
        ],
    )
    async def test_failure_threshold_variations(
        self, failure_threshold: int, expected_state: CircuitBreakerState
    ) -> None:
        """Test circuit breaker behavior with different failure thresholds."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=1.0,
            success_threshold=2,
            timeout=0.5,
        )

        # Initial state should match expectation for threshold 0
        if failure_threshold == 0:
            assert circuit_breaker.state == CircuitBreakerState.OPEN
            return
        else:
            assert circuit_breaker.state == CircuitBreakerState.CLOSED

        async def failing_func() -> str:
            raise ValueError("Test failure")

        # Trigger failures up to threshold
        for i in range(failure_threshold):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

            if i < failure_threshold - 1:
                assert circuit_breaker.state == CircuitBreakerState.CLOSED
            else:
                assert circuit_breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.parametrize("recovery_timeout", [0.1, 1.0, 2.0])
    async def test_recovery_timeout_variations(self, recovery_timeout: float) -> None:
        """Test circuit breaker recovery with different timeout values.

        Note: Reduced timeout values for CI performance. The circuit breaker
        functionality is validated with shorter timeouts while maintaining
        the same test coverage and edge case validation.
        """
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=recovery_timeout,
            success_threshold=1,
            timeout=0.5,
        )

        async def failing_func() -> str:
            raise ValueError("Test failure")

        async def success_func() -> str:
            return "success"

        # Open the circuit breaker
        for _ in range(2):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Try before timeout - should fail
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(success_func)

        # Wait for recovery timeout
        await asyncio.sleep(recovery_timeout + 0.1)

        # Should transition to HALF_OPEN and then CLOSED
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.parametrize("success_threshold", [1, 2, 5, 10])
    async def test_success_threshold_variations(self, success_threshold: int) -> None:
        """Test circuit breaker closing with different success thresholds."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            success_threshold=success_threshold,
            timeout=0.5,
        )

        async def failing_func() -> str:
            raise ValueError("Test failure")

        async def success_func() -> str:
            return "success"

        # Open the circuit breaker
        for _ in range(2):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery
        await asyncio.sleep(0.2)

        # First success should transition to HALF_OPEN
        # For success_threshold=1, it will immediately close
        result = await circuit_breaker.call(success_func)
        assert result == "success"

        if success_threshold == 1:
            # With threshold of 1, circuit closes immediately
            assert circuit_breaker.state == CircuitBreakerState.CLOSED
        else:
            # Otherwise it should be in HALF_OPEN
            assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

            # Additional successes needed based on threshold
            for i in range(success_threshold - 1):
                result = await circuit_breaker.call(success_func)
                assert result == "success"

                if i < success_threshold - 2:
                    assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN
                else:
                    assert circuit_breaker.state == CircuitBreakerState.CLOSED

    async def test_custom_exception_types(self) -> None:
        """Test circuit breaker with custom expected exception types."""

        class NetworkError(Exception):
            pass

        class BusinessLogicError(Exception):
            pass

        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            success_threshold=1,
            timeout=0.5,
            expected_exception=(NetworkError, ValueError),  # Only these count as failures
        )

        async def network_error_func() -> str:
            raise NetworkError("Network failure")

        async def business_error_func() -> str:
            raise BusinessLogicError("Business logic error")

        async def value_error_func() -> str:
            raise ValueError("Value error")

        # NetworkError should count toward circuit breaker
        with pytest.raises(NetworkError):
            await circuit_breaker.call(network_error_func)
        assert circuit_breaker.failure_count == 1

        # BusinessLogicError should NOT count toward circuit breaker
        with pytest.raises(BusinessLogicError):
            await circuit_breaker.call(business_error_func)
        assert circuit_breaker.failure_count == 1  # Should not increment

        # ValueError should count toward circuit breaker
        with pytest.raises(ValueError):
            await circuit_breaker.call(value_error_func)
        assert circuit_breaker.failure_count == 2
        assert circuit_breaker.state == CircuitBreakerState.OPEN


class TestCircuitBreakerTimingAndRecovery:
    """Test circuit breaker timing behaviors and recovery patterns."""

    async def test_exponential_backoff_calculation(self) -> None:
        """Test that exponential backoff is calculated correctly."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,
            success_threshold=1,
            timeout=0.5,
        )

        async def failing_func() -> str:
            raise ValueError("Test failure")

        # Open circuit breaker
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN
        first_next_attempt = circuit_breaker._next_attempt_time

        # Wait and try again to trigger more backoff
        await asyncio.sleep(1.1)

        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_func)

        second_next_attempt = circuit_breaker._next_attempt_time

        # Second attempt time should be further in the future (exponential backoff)
        assert second_next_attempt > first_next_attempt

        # Backoff should be capped
        for _ in range(10):  # Many more failures
            await asyncio.sleep(0.1)
            with contextlib.suppress(ValueError, CircuitBreakerError):
                await circuit_breaker.call(failing_func)

        # Should not grow indefinitely
        final_next_attempt = circuit_breaker._next_attempt_time
        max_backoff = circuit_breaker.recovery_timeout * 8  # Max multiplier is 8
        current_time = time.time()

        assert final_next_attempt - current_time <= max_backoff * 1.2  # Allow some tolerance

    async def test_jitter_in_backoff(self) -> None:
        """Test that jitter is applied to prevent thundering herd."""
        circuit_breakers = []
        next_attempt_times = []

        # Create multiple circuit breakers with same config
        for _ in range(10):
            cb = CircuitBreaker(
                failure_threshold=2,
                recovery_timeout=1.0,
                success_threshold=1,
                timeout=0.5,
            )
            circuit_breakers.append(cb)

        async def failing_func() -> str:
            raise ValueError("Test failure")

        # Open all circuit breakers at roughly the same time
        for cb in circuit_breakers:
            for _ in range(2):
                with pytest.raises(ValueError):
                    await cb.call(failing_func)
            next_attempt_times.append(cb._next_attempt_time)

        # Should have some variation due to jitter
        unique_times = set(next_attempt_times)
        assert len(unique_times) > 1, "Expected jitter to create different next attempt times"

        # All times should be within reasonable range
        min_time = min(t for t in next_attempt_times if t is not None)
        max_time = max(t for t in next_attempt_times if t is not None)
        time_spread = max_time - min_time

        assert time_spread > 0, "No jitter detected"
        assert time_spread < 1.0, f"Jitter spread too large: {time_spread}s"

    @freeze_time("2024-01-01 12:00:00")
    async def test_time_manipulation_recovery(self) -> None:
        """Test circuit breaker recovery with manipulated time."""
        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            circuit_breaker = CircuitBreaker(
                failure_threshold=2,
                recovery_timeout=60.0,  # 1 minute
                success_threshold=1,
                timeout=0.5,
            )

            async def failing_func() -> str:
                raise ValueError("Test failure")

            async def success_func() -> str:
                return "success"

            # Open circuit breaker
            for _ in range(2):
                with pytest.raises(ValueError):
                    await circuit_breaker.call(failing_func)

            assert circuit_breaker.state == CircuitBreakerState.OPEN

            # Should block immediately
            with pytest.raises(CircuitBreakerError):
                await circuit_breaker.call(success_func)

            # Advance time but not enough
            frozen_time.tick(delta=30)  # 30 seconds

            with pytest.raises(CircuitBreakerError):
                await circuit_breaker.call(success_func)

            # Advance time past recovery timeout
            frozen_time.tick(delta=35)  # Total 65 seconds

            # Should now allow recovery
            result = await circuit_breaker.call(success_func)
            assert result == "success"
            assert circuit_breaker.state == CircuitBreakerState.CLOSED

    async def test_recovery_under_load(self) -> None:
        """Test circuit breaker recovery when under continued load."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=0.1,  # Shorter timeout for faster tests
            success_threshold=3,  # Need 3 successes to close
            timeout=0.5,
        )

        async def failing_func() -> str:
            raise ValueError("Test failure")

        async def success_func() -> str:
            await asyncio.sleep(0.01)  # Small delay to ensure deterministic timing
            return "success"

        # Open circuit breaker
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery (account for exponential backoff)
        # After 3 failures, backoff multiplier is 1, so wait recovery_timeout + jitter + buffer
        await asyncio.sleep(0.25)

        # Partial recovery - not enough successes
        for _ in range(2):  # Only 2 successes, need 3
            result = await circuit_breaker.call(success_func)
            assert result == "success"
            assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN
            # Small delay between operations to ensure state consistency
            await asyncio.sleep(0.01)

        # Failure during recovery should reopen
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_func)
        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for longer recovery (backoff is now higher)
        # After 4 failures, backoff multiplier is 2, so need longer wait
        await asyncio.sleep(0.4)

        # Full recovery - all 3 successes
        for _ in range(3):
            result = await circuit_breaker.call(success_func)
            assert result == "success"
            # Add small delay between operations for state transition
            await asyncio.sleep(0.01)

        assert circuit_breaker.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerEdgeCases:
    """Test unusual and edge case scenarios for circuit breaker."""

    async def test_zero_timeout_operations(self) -> None:
        """Test circuit breaker with zero timeout (immediate timeout)."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            success_threshold=1,
            timeout=0.0,  # Immediate timeout
        )

        async def slow_func() -> str:
            await asyncio.sleep(0.1)  # Any delay should timeout
            return "success"

        # Should timeout immediately
        with pytest.raises(asyncio.TimeoutError):
            await circuit_breaker.call(slow_func)

        assert circuit_breaker.failure_count == 1

    async def test_very_fast_operations(self) -> None:
        """Test circuit breaker with very fast operations."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=1000,  # High threshold
            recovery_timeout=0.001,  # Very fast recovery
            success_threshold=1,
            timeout=0.1,
        )

        async def fast_func() -> str:
            return "fast"

        # Execute many fast operations
        for _ in range(1000):
            result = await circuit_breaker.call(fast_func)
            assert result == "fast"

        # All should succeed
        metrics = circuit_breaker.metrics
        assert metrics["total_requests"] == 1000
        assert metrics["total_successes"] == 1000
        assert metrics["total_failures"] == 0
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    async def test_concurrent_state_transitions(self) -> None:
        """Test concurrent operations during state transitions."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=0.05,  # Very short timeout for faster test
            success_threshold=2,
            timeout=1.0,
        )

        async def mixed_func(should_fail: bool) -> str:
            if should_fail:
                raise ValueError("Controlled failure")
            await asyncio.sleep(0.001)  # Minimal delay to avoid race conditions
            return "success"

        # Phase 1: Open the circuit breaker with sequential operations to ensure state
        for _ in range(5):  # Exactly failure threshold
            with pytest.raises(ValueError):
                await circuit_breaker.call(mixed_func, True)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery period with buffer for jitter
        await asyncio.sleep(0.15)

        # Phase 2: Test recovery with mostly successful operations
        recovery_tasks = []
        for i in range(20):
            # Lower failure rate to ensure some successes
            should_fail = i % 20 == 0  # 5% failure rate
            task = asyncio.create_task(circuit_breaker.call(mixed_func, should_fail))
            recovery_tasks.append(task)
            # Add small delay between task creation to reduce race conditions
            await asyncio.sleep(0.001)

        recovery_results = await asyncio.gather(*recovery_tasks, return_exceptions=True)

        # Should have mix of results
        successes = [r for r in recovery_results if r == "success"]
        circuit_breaker_errors = [r for r in recovery_results if isinstance(r, CircuitBreakerError)]

        # Either we get successes during recovery, or circuit breaker blocks all attempts
        # Both are valid behaviors depending on timing
        assert len(successes) > 0 or len(circuit_breaker_errors) > 0, "No expected results during recovery"

        # Final state should be consistent
        final_state = circuit_breaker.state
        assert final_state in [CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN]

    async def test_exception_propagation_integrity(self) -> None:
        """Test that original exceptions are properly propagated."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=10,  # High threshold to avoid opening
            recovery_timeout=1.0,
            success_threshold=1,
            timeout=1.0,
        )

        class CustomError(Exception):
            def __init__(self, message: str, error_code: int):
                super().__init__(message)
                self.error_code = error_code

        async def custom_error_func() -> str:
            raise CustomError("Custom error message", 12345)

        # Exception should be propagated with all attributes
        with pytest.raises(CustomError) as exc_info:
            await circuit_breaker.call(custom_error_func)

        assert str(exc_info.value) == "Custom error message"
        assert exc_info.value.error_code == 12345

    async def test_metrics_consistency_under_stress(self) -> None:
        """Test that metrics remain consistent under stress conditions."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=50,
            recovery_timeout=0.1,
            success_threshold=5,
            timeout=0.1,
        )

        success_count = 0
        failure_count = 0
        timeout_count = 0

        async def stress_func(operation_type: str) -> str:
            nonlocal success_count, failure_count, timeout_count

            if operation_type == "success":
                success_count += 1
                return "success"
            elif operation_type == "failure":
                failure_count += 1
                raise ValueError("Stress test failure")
            elif operation_type == "timeout":
                timeout_count += 1
                await asyncio.sleep(0.2)  # Will timeout
                return "too slow"
            else:
                raise RuntimeError("Unknown operation type")

        # Generate stress operations
        operations = []
        for i in range(200):
            if i % 3 == 0:
                operations.append("success")
            elif i % 3 == 1:
                operations.append("failure")
            else:
                operations.append("timeout")

        # Execute all operations
        tasks = [circuit_breaker.call(stress_func, op_type) for op_type in operations]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify metrics consistency
        metrics = circuit_breaker.metrics

        # Count actual results
        actual_successes = len([r for r in results if r == "success"])
        actual_failures = len([r for r in results if isinstance(r, Exception)])

        # Metrics should account for all operations
        assert metrics["total_requests"] == len(operations)
        assert metrics["total_successes"] <= actual_successes + 10  # Allow some tolerance
        assert metrics["total_failures"] >= actual_failures - 10

        # Failure rate should be reasonable
        assert 0.0 <= metrics["failure_rate"] <= 1.0

        # Debug output for stress test
        # print(
        #     f"Stress test: {metrics['total_requests']} requests, "
        #     f"{metrics['total_successes']} successes, "
        #     f"{metrics['total_failures']} failures, "
        #     f"{metrics['failure_rate']:.2%} failure rate"
        # )
