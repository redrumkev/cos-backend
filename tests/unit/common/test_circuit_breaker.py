"""Comprehensive unit tests for Circuit Breaker implementation."""

import asyncio
import time
from typing import Any

import pytest
from freezegun import freeze_time

from src.common.pubsub import CircuitBreaker, CircuitBreakerError, CircuitBreakerState


class TestCircuitBreaker:
    """Test suite for CircuitBreaker class."""

    @pytest.fixture
    def circuit_breaker(self, circuit_breaker_config: dict[str, Any]) -> CircuitBreaker:
        """Create CircuitBreaker instance for testing."""
        return CircuitBreaker(**circuit_breaker_config)

    @pytest.fixture
    def zero_threshold_breaker(self) -> CircuitBreaker:
        """Circuit breaker that opens immediately on any failure."""
        return CircuitBreaker(failure_threshold=0, recovery_timeout=1.0)

    async def test_init_default_values(self) -> None:
        """Test CircuitBreaker initialization with default values."""
        cb = CircuitBreaker()

        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60.0
        assert cb.success_threshold == 3
        assert cb.timeout == 10.0
        assert cb.expected_exception is Exception
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    async def test_init_custom_values(self) -> None:
        """Test CircuitBreaker initialization with custom values."""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=30.0,
            success_threshold=1,
            timeout=5.0,
            expected_exception=ValueError,
        )

        assert cb.failure_threshold == 2
        assert cb.recovery_timeout == 30.0
        assert cb.success_threshold == 1
        assert cb.timeout == 5.0
        assert cb.expected_exception is ValueError

    async def test_init_zero_threshold_opens_immediately(self) -> None:
        """Test that zero failure threshold starts in OPEN state."""
        cb = CircuitBreaker(failure_threshold=0)

        assert cb.state == CircuitBreakerState.OPEN
        assert cb._next_attempt_time == float("inf")

    async def test_properties(self, circuit_breaker: CircuitBreaker) -> None:
        """Test CircuitBreaker properties."""
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0

        # Test metrics property
        metrics = circuit_breaker.metrics
        assert "state" in metrics
        assert "failure_count" in metrics
        assert "total_requests" in metrics
        assert "failure_rate" in metrics
        assert "state_transitions" in metrics

    async def test_successful_operation(self, circuit_breaker: CircuitBreaker) -> None:
        """Test successful operation through circuit breaker."""

        async def successful_operation() -> str:
            return "success"

        result = await circuit_breaker.call(successful_operation)

        assert result == "success"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0
        metrics = circuit_breaker.metrics
        assert metrics["total_requests"] == 1
        assert metrics["total_successes"] == 1

    async def test_operation_with_timeout(self, circuit_breaker: CircuitBreaker) -> None:
        """Test operation timeout handling."""

        async def slow_operation() -> str:
            await asyncio.sleep(1.0)  # Longer than timeout
            return "success"

        with pytest.raises(asyncio.TimeoutError):
            await circuit_breaker.call(slow_operation)

        # Should record as failure
        assert circuit_breaker.failure_count == 1
        metrics = circuit_breaker.metrics
        assert metrics["total_failures"] == 1

    async def test_operation_with_expected_exception(self, circuit_breaker: CircuitBreaker) -> None:
        """Test operation that raises expected exception."""

        async def failing_operation() -> str:
            raise ValueError("Expected failure")

        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_operation)

        assert circuit_breaker.failure_count == 1
        metrics = circuit_breaker.metrics
        assert metrics["total_failures"] == 1

    async def test_operation_with_unexpected_exception(self, circuit_breaker: CircuitBreaker) -> None:
        """Test operation that raises unexpected exception."""
        # Circuit breaker configured to expect Exception (default)
        cb = CircuitBreaker(expected_exception=ValueError)

        async def failing_operation() -> str:
            raise RuntimeError("Unexpected failure")

        with pytest.raises(RuntimeError):
            await cb.call(failing_operation)

        # Should NOT count as circuit breaker failure
        assert cb.failure_count == 0
        metrics = cb.metrics
        assert metrics["total_requests"] == 1
        assert metrics["total_failures"] == 0

    async def test_transition_to_open_state(self, circuit_breaker: CircuitBreaker) -> None:
        """Test transition from CLOSED to OPEN state."""

        async def failing_operation() -> str:
            raise ValueError("Failure")

        # Trigger failures to reach threshold
        for i in range(3):  # failure_threshold = 3
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_operation)

            if i < 2:  # Before threshold
                assert circuit_breaker.state == CircuitBreakerState.CLOSED
            else:  # At threshold
                assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Check state transition metrics
        metrics = circuit_breaker.metrics
        assert metrics["state_transitions"]["closed_to_open"] == 1

    async def test_open_state_blocks_requests(self, circuit_breaker: CircuitBreaker) -> None:
        """Test that OPEN state blocks new requests."""
        # Force to OPEN state
        circuit_breaker._state = CircuitBreakerState.OPEN
        circuit_breaker._next_attempt_time = time.time() + 3600  # 1 hour from now

        async def operation() -> str:
            return "success"

        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(operation)

    @freeze_time("2023-01-01 00:00:00")
    async def test_transition_to_half_open_after_timeout(self, circuit_breaker: CircuitBreaker) -> None:
        """Test transition from OPEN to HALF_OPEN after recovery timeout."""

        async def failing_operation() -> str:
            raise ValueError("Failure")

        # Trigger failures to open circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_operation)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Move time forward past recovery timeout
        with freeze_time("2023-01-01 00:00:02"):  # 2 seconds later (> 1.0 recovery_timeout)

            async def successful_operation() -> str:
                return "success"

            result = await circuit_breaker.call(successful_operation)

            assert result == "success"
            assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN  # type: ignore[comparison-overlap]

    async def test_half_open_to_closed_transition(self, circuit_breaker: CircuitBreaker) -> None:
        """Test transition from HALF_OPEN to CLOSED after successful operations."""
        # Force to HALF_OPEN state
        circuit_breaker._state = CircuitBreakerState.HALF_OPEN
        circuit_breaker._success_count = 0

        async def successful_operation() -> str:
            return "success"

        # Perform successful operations to reach success threshold
        for i in range(2):  # success_threshold = 2
            result = await circuit_breaker.call(successful_operation)
            assert result == "success"

            if i < 1:  # Before threshold
                assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN
            else:  # At threshold
                assert circuit_breaker.state == CircuitBreakerState.CLOSED

        # Verify state was reset
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0

    async def test_half_open_to_open_on_failure(self, circuit_breaker: CircuitBreaker) -> None:
        """Test transition from HALF_OPEN back to OPEN on failure."""
        # Force to HALF_OPEN state
        circuit_breaker._state = CircuitBreakerState.HALF_OPEN

        async def failing_operation() -> str:
            raise ValueError("Failure")

        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_operation)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Check state transition metrics
        metrics = circuit_breaker.metrics
        assert metrics["state_transitions"]["half_open_to_open"] == 1

    async def test_zero_threshold_behavior(self, zero_threshold_breaker: CircuitBreaker) -> None:
        """Test circuit breaker with zero failure threshold."""
        assert zero_threshold_breaker.state == CircuitBreakerState.OPEN

        async def operation() -> str:
            return "success"

        # Should always block requests
        with pytest.raises(CircuitBreakerError):
            await zero_threshold_breaker.call(operation)

    async def test_concurrent_operations(self, circuit_breaker: CircuitBreaker) -> None:
        """Test circuit breaker thread safety with concurrent operations."""
        results = []
        errors = []

        async def operation(delay: float) -> str:
            await asyncio.sleep(delay)
            return f"success-{delay}"

        async def failing_operation() -> str:
            raise ValueError("Failure")

        # Run concurrent operations
        tasks = [
            circuit_breaker.call(operation, 0.1),
            circuit_breaker.call(operation, 0.05),
            circuit_breaker.call(failing_operation),
            circuit_breaker.call(operation, 0.02),
        ]

        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                results.append(result)
            except Exception as exc:
                errors.append(exc)

        # Verify at least some operations succeeded
        assert len(results) >= 3
        assert len(errors) >= 1

    async def test_metrics_tracking(self, circuit_breaker: CircuitBreaker) -> None:
        """Test comprehensive metrics tracking."""

        async def successful_operation() -> str:
            return "success"

        async def failing_operation() -> str:
            raise ValueError("Failure")

        # Perform mixed operations
        await circuit_breaker.call(successful_operation)

        import contextlib

        with contextlib.suppress(ValueError):
            await circuit_breaker.call(failing_operation)

        await circuit_breaker.call(successful_operation)

        metrics = circuit_breaker.metrics
        assert metrics["total_requests"] == 3
        assert metrics["total_successes"] == 2
        assert metrics["total_failures"] == 1
        assert metrics["failure_rate"] == 1 / 3

    async def test_exponential_backoff_with_jitter(self, circuit_breaker: CircuitBreaker) -> None:
        """Test exponential backoff calculation with jitter."""

        async def failing_operation() -> str:
            raise ValueError("Failure")

        # Trigger multiple failures to test backoff calculation
        for _ in range(5):  # More than threshold to test backoff
            import contextlib

            with contextlib.suppress(ValueError, CircuitBreakerError):
                await circuit_breaker.call(failing_operation)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Check that next attempt time was calculated with backoff
        metrics = circuit_breaker.metrics
        assert metrics["next_attempt_time"] is not None
        assert metrics["next_attempt_time"] > time.time()

    async def test_state_reset_on_close(self, circuit_breaker: CircuitBreaker) -> None:
        """Test that state is properly reset when circuit closes."""
        # Force circuit to HALF_OPEN state first
        circuit_breaker._state = CircuitBreakerState.HALF_OPEN

        # Force some state
        circuit_breaker._failure_count = 5
        circuit_breaker._success_count = 3
        circuit_breaker._last_failure_time = time.time()
        circuit_breaker._next_attempt_time = time.time() + 100

        # Force transition to closed
        await circuit_breaker._transition_to_closed()

        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0
        assert circuit_breaker._last_failure_time is None
        assert circuit_breaker._next_attempt_time is None

    async def test_complex_state_machine_transitions(self, circuit_breaker: CircuitBreaker) -> None:
        """Test complex state machine scenarios."""

        async def operation(should_fail: bool) -> str:
            if should_fail:
                raise ValueError("Failure")
            return "success"

        # Start in CLOSED
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        # Trigger failures to open
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(operation, True)

        assert circuit_breaker.state == CircuitBreakerState.OPEN  # type: ignore[comparison-overlap]

        # Move to HALF_OPEN (need to mock time passage)
        circuit_breaker._next_attempt_time = time.time() - 1  # Past time

        # One success moves to HALF_OPEN, another should close
        await circuit_breaker.call(operation, False)
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

        await circuit_breaker.call(operation, False)
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.benchmark
    async def test_circuit_breaker_performance(self, circuit_breaker: CircuitBreaker) -> None:
        """Test circuit breaker performance overhead."""

        async def fast_operation() -> str:
            return "success"

        # Measure overhead
        start_time = time.perf_counter()

        for _ in range(1000):
            await circuit_breaker.call(fast_operation)

        elapsed = time.perf_counter() - start_time

        # Should complete 1000 operations quickly (adjust threshold as needed)
        assert elapsed < 1.0, f"Circuit breaker overhead too high: {elapsed:.3f}s"

        # Verify all operations succeeded
        metrics = circuit_breaker.metrics
        assert metrics["total_requests"] == 1000
        assert metrics["total_successes"] == 1000
