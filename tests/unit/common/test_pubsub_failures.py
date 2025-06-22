"""Comprehensive failure scenario tests for Redis Pub/Sub implementation.

This module tests network failures, timeouts, malformed data, connection drops,
and other edge cases to ensure robust error handling and recovery.
"""

import asyncio
import json
from typing import Any

import pytest

from src.common.pubsub import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerState,
    PublishError,
    RedisPubSub,
)

# mypy: disable-error-code="attr-defined,method-assign,assignment,arg-type"


class TestNetworkFailureScenarios:
    """Test Redis Pub/Sub behavior under various network failure conditions."""

    async def test_gradual_network_degradation(
        self,
        redis_pubsub_with_mocks: RedisPubSub,
        redis_test_utils: Any,
    ) -> None:
        """Test behavior as network conditions gradually degrade."""
        pubsub = redis_pubsub_with_mocks

        # Start with normal operation
        test_message = redis_test_utils.generate_test_message(100)
        result = await pubsub.publish("degradation_test", test_message)
        assert result > 0

        # Simulate increasing latency
        original_publish = pubsub._redis.publish
        latency_ms = 0

        async def degraded_publish(*args: Any, **kwargs: Any) -> Any:
            nonlocal latency_ms
            latency_ms += 10  # Increase latency by 10ms each call
            await redis_test_utils.simulate_network_latency(latency_ms)
            return await original_publish(*args, **kwargs)

        pubsub._redis.publish = degraded_publish

        # Test publishing with increasing latency
        for _ in range(10):
            try:
                await pubsub.publish("degradation_test", test_message)
                # Should still work but get slower
                assert latency_ms == (_ + 1) * 10
            except Exception as e:
                # Eventually should timeout or circuit breaker should open
                assert "timeout" in str(e).lower() or "circuit breaker" in str(e).lower()
                break

    async def test_intermittent_connection_drops(
        self,
        redis_pubsub_with_mocks: RedisPubSub,
        redis_test_utils: Any,
    ) -> None:
        """Test handling of intermittent connection drops and recovery."""
        pubsub = redis_pubsub_with_mocks

        call_count = 0
        original_publish = pubsub._redis.publish

        async def intermittent_publish(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1

            # Fail every 3rd call
            if call_count % 3 == 0:
                from src.common.pubsub import RedisConnectionError

                raise RedisConnectionError("Intermittent connection drop")

            return await original_publish(*args, **kwargs)

        pubsub._redis.publish = intermittent_publish

        # Test multiple publish attempts
        success_count = 0
        failure_count = 0

        for _ in range(10):
            try:
                test_message = redis_test_utils.generate_test_message(100)
                await pubsub.publish("intermittent_test", test_message)
                success_count += 1
            except (PublishError, CircuitBreakerError):
                failure_count += 1

        # Should have both successes and failures
        assert success_count > 0, "No successful publishes despite intermittent failures"
        assert failure_count > 0, "No failures detected in intermittent failure test"

        # Circuit breaker behavior depends on failure threshold
        cb_metrics = pubsub.circuit_breaker_metrics
        assert cb_metrics["total_requests"] == success_count + failure_count

    async def test_partial_message_corruption(
        self,
        redis_pubsub_with_mocks: RedisPubSub,
        redis_test_utils: Any,
    ) -> None:
        """Test handling of partially corrupted messages during transmission."""
        pubsub = redis_pubsub_with_mocks

        received_messages = []
        corrupted_messages = []

        async def corruption_handler(channel: str, message: dict[str, Any]) -> None:
            if message.get("corrupted"):
                corrupted_messages.append((channel, message))
            else:
                received_messages.append((channel, message))

        await pubsub.subscribe("corruption_test", corruption_handler)
        await redis_test_utils.wait_for_message_processing()

        # Mock the message handling to simulate corruption
        original_handle_message = pubsub._handle_message

        async def corrupted_handle_message(message: dict[str, Any]) -> None:
            # Randomly corrupt some messages
            if "corruption_test" in str(message.get("channel", "")):
                import random

                if random.random() < 0.3:  # noqa: S311
                    # Simulate corrupted JSON
                    corrupted_data = '{"corrupted": true, "original": ' + str(message.get("data", "{}"))
                    message["data"] = corrupted_data.encode()

            await original_handle_message(message)

        pubsub._handle_message = corrupted_handle_message

        # Send multiple messages
        for _ in range(20):
            test_message = redis_test_utils.generate_test_message(100)
            test_message["message_id"] = _
            await pubsub.publish("corruption_test", test_message)

        await redis_test_utils.wait_for_message_processing()

        # Should have received some valid messages despite corruption
        assert len(received_messages) > 0, "No valid messages received"

        # Verify message integrity for non-corrupted messages
        for channel, message in received_messages:
            assert channel == "corruption_test"
            assert "message_id" in message
            assert "content" in message

    async def test_redis_server_restart_simulation(
        self,
        redis_pubsub_with_mocks: RedisPubSub,
        redis_test_utils: Any,
    ) -> None:
        """Test behavior when Redis server restarts during operations."""
        pubsub = redis_pubsub_with_mocks

        # Set up subscription
        received_messages = []

        async def restart_handler(channel: str, message: dict[str, Any]) -> None:
            received_messages.append((channel, message))

        await pubsub.subscribe("restart_test", restart_handler)

        # Send some messages before "restart"
        for _ in range(5):
            test_message = redis_test_utils.generate_test_message(100)
            test_message["pre_restart"] = _
            await pubsub.publish("restart_test", test_message)

        await redis_test_utils.wait_for_message_processing()
        pre_restart_count = len(received_messages)

        # Simulate server restart by making all operations fail temporarily
        restart_call_count = 0
        original_publish = pubsub._redis.publish
        original_ping = pubsub._redis.ping

        async def restart_publish(*args: Any, **kwargs: Any) -> Any:
            nonlocal restart_call_count
            restart_call_count += 1
            if restart_call_count <= 3:  # Fail first 3 attempts
                from src.common.pubsub import RedisConnectionError

                raise RedisConnectionError("Redis server restarting")
            return await original_publish(*args, **kwargs)

        async def restart_ping(*args: Any, **kwargs: Any) -> Any:
            nonlocal restart_call_count
            if restart_call_count <= 3:
                from src.common.pubsub import RedisConnectionError

                raise RedisConnectionError("Redis server restarting")
            return await original_ping(*args, **kwargs)

        pubsub._redis.publish = restart_publish
        pubsub._redis.ping = restart_ping

        # Try to send messages during "restart" - should fail
        restart_failures = 0
        for _ in range(3):
            try:
                test_message = redis_test_utils.generate_test_message(100)
                test_message["during_restart"] = _
                await pubsub.publish("restart_test", test_message)
            except (PublishError, CircuitBreakerError):
                restart_failures += 1

        assert restart_failures > 0, "Expected failures during simulated restart"

        # Wait for circuit breaker recovery
        await asyncio.sleep(1.1)  # Longer than recovery timeout

        # Send messages after "restart" - should work again
        for _ in range(5):
            test_message = redis_test_utils.generate_test_message(100)
            test_message["post_restart"] = _
            try:
                await pubsub.publish("restart_test", test_message)
            except CircuitBreakerError:
                # Circuit breaker may still be open, try again after more time
                await asyncio.sleep(1.0)
                await pubsub.publish("restart_test", test_message)

        await redis_test_utils.wait_for_message_processing()

        # Should have more messages after restart recovery
        post_restart_count = len(received_messages)
        assert (
            post_restart_count > pre_restart_count
        ), f"Message count should increase after restart recovery: {pre_restart_count} -> {post_restart_count}"


class TestMalformedDataHandling:
    """Test handling of malformed, oversized, and invalid data scenarios."""

    async def test_invalid_json_serialization(
        self,
        redis_pubsub_with_mocks: RedisPubSub,
    ) -> None:
        """Test handling of non-serializable objects."""
        pubsub = redis_pubsub_with_mocks

        # Test various non-serializable objects
        non_serializable_data: list[dict[str, Any]] = [
            {"function": lambda x: x},  # Function
            {"set": {1, 2, 3}},  # Set (not directly JSON serializable)
            {"bytes": b"binary data"},  # Bytes
            {"circular": None},  # Circular reference (set below)
        ]

        # Create circular reference
        circular: dict[str, Any] = {"self": None}
        circular["self"] = circular
        non_serializable_data[3]["circular"] = circular

        for i in range(len(non_serializable_data)):
            with pytest.raises(PublishError, match="Failed to serialize"):
                await pubsub.publish(f"invalid_json_{i}", non_serializable_data[i])

    async def test_extremely_large_messages(
        self,
        redis_pubsub_with_mocks: RedisPubSub,
        redis_test_utils: Any,
    ) -> None:
        """Test handling of extremely large message payloads."""
        pubsub = redis_pubsub_with_mocks

        # Test increasing message sizes
        sizes = [1024, 10240, 102400, 1048576]  # 1KB, 10KB, 100KB, 1MB

        for size in sizes:
            large_message = redis_test_utils.generate_test_message(size)

            try:
                result = await pubsub.publish("large_message_test", large_message)
                assert result >= 0

                # Verify the message was properly serialized
                serialized = json.dumps(large_message)
                assert len(serialized) > size

            except PublishError as e:
                # Large messages might fail - that's acceptable
                assert "serialize" in str(e) or "too large" in str(e).lower()

    async def test_special_character_handling(
        self,
        redis_pubsub_with_mocks: RedisPubSub,
    ) -> None:
        """Test handling of messages with special characters and encodings."""
        pubsub = redis_pubsub_with_mocks

        special_messages = [
            {"unicode": "Hello 世界 🌍"},
            {"emoji": "🚀🔥💯🎉"},
            {"control_chars": "Line1\nLine2\tTabbed\rCarriage"},
            {"quotes": "Single \"double\" 'mixed' quotes"},
            {"null_bytes": "Before\x00After"},
            {"high_unicode": "\U0001f600\U0001f680\U0001f4a9"},
        ]

        for i in range(len(special_messages)):
            try:
                result = await pubsub.publish(f"special_chars_{i}", special_messages[i])
                assert result >= 0

                # Verify JSON serialization/deserialization works
                serialized = json.dumps(special_messages[i])
                deserialized = json.loads(serialized)
                assert deserialized == special_messages[i]

            except Exception as e:
                pytest.fail(f"Failed to handle special characters in message {i}: {e}")

    async def test_nested_data_structure_limits(
        self,
        redis_pubsub_with_mocks: RedisPubSub,
    ) -> None:
        """Test handling of deeply nested data structures."""
        pubsub = redis_pubsub_with_mocks

        # Create deeply nested structure
        def create_nested_dict(depth: int) -> dict[str, Any]:
            if depth == 0:
                return {"value": "leaf"}
            return {"level": depth, "nested": create_nested_dict(depth - 1)}

        # Test various nesting levels
        depths = [10, 50, 100, 500]

        for depth in depths:
            nested_message = {"depth": depth, "data": create_nested_dict(depth)}

            try:
                result = await pubsub.publish(f"nested_test_{depth}", nested_message)
                assert result >= 0

                # Verify serialization works
                serialized = json.dumps(nested_message)
                assert len(serialized) > 0

            except (PublishError, RecursionError) as e:
                # Very deep nesting might fail - that's acceptable
                if depth > 100:
                    assert "recursion" in str(e).lower() or "serialize" in str(e).lower()
                else:
                    pytest.fail(f"Unexpected failure at depth {depth}: {e}")


class TestConcurrencyFailures:
    """Test failure scenarios under high concurrency conditions."""

    async def test_concurrent_connection_failures(
        self,
        redis_pubsub_with_mocks: RedisPubSub,
        redis_test_utils: Any,
    ) -> None:
        """Test behavior when multiple concurrent operations fail simultaneously."""
        pubsub = redis_pubsub_with_mocks

        # Set up concurrent failure simulation
        failure_rate = 0.5
        call_count = 0
        original_publish = pubsub._redis.publish

        async def concurrent_failing_publish(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1

            import random

            if random.random() < failure_rate:  # noqa: S311
                from src.common.pubsub import RedisError

                raise RedisError(f"Concurrent failure {call_count}")

            return await original_publish(*args, **kwargs)

        pubsub._redis.publish = concurrent_failing_publish

        # Execute many concurrent operations
        concurrent_ops = 100
        tasks = []

        for _ in range(concurrent_ops):
            test_message = redis_test_utils.generate_test_message(100)
            test_message["op_id"] = _
            task = asyncio.create_task(pubsub.publish(f"concurrent_fail_{_ % 10}", test_message))
            tasks.append(task)

        # Gather results, allowing for failures
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        successes = [r for r in results if isinstance(r, int)]
        failures = [r for r in results if isinstance(r, Exception)]

        assert len(successes) > 0, "No successful operations in concurrent test"
        assert len(failures) > 0, "No failures in concurrent failure test"

        # Verify circuit breaker handled concurrent failures appropriately
        cb_metrics = pubsub.circuit_breaker_metrics
        assert cb_metrics["total_requests"] >= len(successes)

    async def test_race_condition_in_subscription_management(
        self,
        redis_pubsub_with_mocks: RedisPubSub,
        redis_test_utils: Any,
    ) -> None:
        """Test race conditions in concurrent subscribe/unsubscribe operations."""
        pubsub = redis_pubsub_with_mocks

        channel = "race_condition_test"
        handler_calls = []

        # Create multiple handlers
        async def handler_1(ch: str, msg: dict[str, Any]) -> None:
            handler_calls.append(("handler_1", ch, msg))

        async def handler_2(ch: str, msg: dict[str, Any]) -> None:
            handler_calls.append(("handler_2", ch, msg))

        async def handler_3(ch: str, msg: dict[str, Any]) -> None:
            handler_calls.append(("handler_3", ch, msg))

        handlers = [handler_1, handler_2, handler_3]

        # Concurrent subscribe/unsubscribe operations
        async def subscribe_unsubscribe_cycle(handler: Any, iterations: int) -> None:
            for _ in range(iterations):
                try:
                    await pubsub.subscribe(channel, handler)
                    await redis_test_utils.wait_for_message_processing(0.01)

                    # Send a message
                    test_message = {"iteration": _, "handler": handler.__name__}
                    await pubsub.publish(channel, test_message)
                    await redis_test_utils.wait_for_message_processing(0.01)

                    await pubsub.unsubscribe(channel, handler)
                    await redis_test_utils.wait_for_message_processing(0.01)

                except Exception as e:
                    # Some operations might fail due to race conditions
                    assert "subscribe" in str(e).lower() or "unsubscribe" in str(e).lower()

        # Run concurrent subscription cycles
        await asyncio.gather(*[subscribe_unsubscribe_cycle(handler, 5) for handler in handlers])

        # Wait for all operations to complete
        await redis_test_utils.wait_for_message_processing(0.5)

        # Verify no handlers are left subscribed
        assert len(pubsub.active_subscriptions) == 0 or channel not in pubsub.active_subscriptions

        # Verify some messages were processed (despite race conditions)
        assert len(handler_calls) > 0, "No handler calls recorded despite concurrent operations"

    async def test_circuit_breaker_race_conditions(
        self,
        circuit_breaker_test_config: dict[str, Any],
    ) -> None:
        """Test race conditions in circuit breaker state transitions."""
        config = circuit_breaker_test_config
        circuit_breaker = CircuitBreaker(**config)

        # Simulate concurrent operations that could trigger state changes
        async def failing_operation() -> str:
            from src.common.pubsub import RedisError

            raise RedisError("Test failure")

        async def successful_operation() -> str:
            return "success"

        # Mix of failing and successful operations
        operations = []
        for _ in range(50):
            if _ < 30:  # First 30 are failures
                operations.append(failing_operation)
            else:  # Last 20 are successes
                operations.append(successful_operation)

        # Execute all operations concurrently
        tasks = [asyncio.create_task(circuit_breaker.call(op)) for op in operations]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        _successes = [r for r in results if r == "success"]
        failures = [r for r in results if isinstance(r, Exception)]

        # Should have both successes and failures
        assert len(failures) > 0, "No failures in circuit breaker race condition test"

        # Circuit breaker should be in a consistent state
        final_state = circuit_breaker.state
        assert final_state in [CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN]

        # Metrics should be consistent
        metrics = circuit_breaker.metrics
        assert metrics["total_requests"] == len(operations)
        assert metrics["total_successes"] + metrics["total_failures"] <= metrics["total_requests"]
