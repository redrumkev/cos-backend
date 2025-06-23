"""Quick coverage check for Redis pub/sub components."""

from unittest.mock import patch

from src.common.base_subscriber import BaseSubscriber
from src.common.pubsub import CircuitBreaker, RedisPubSub, cleanup_pubsub
from src.common.redis_config import RedisConfig, get_redis_config


class MinimalSubscriber(BaseSubscriber):
    """Minimal subscriber for testing."""

    async def process_message(self, message: dict[str, Any]) -> bool:
        return True


class TestCoverageCheck:
    """Quick tests to ensure basic coverage."""

    def test_circuit_breaker_basic(self) -> None:
        """Test basic circuit breaker functionality."""
        cb = CircuitBreaker()
        assert cb.state.value == "closed"
        assert cb.failure_count == 0

    def test_redis_config_basic(self) -> None:
        """Test basic Redis config functionality."""
        config = RedisConfig()
        assert config.redis_host == "localhost"
        assert config.redis_port == 6379
        assert config.redis_url.startswith("redis://")

    def test_redis_config_caching(self) -> None:
        """Test Redis config caching."""
        config1 = get_redis_config()
        config2 = get_redis_config()
        assert config1 is config2

    def test_base_subscriber_init(self) -> None:
        """Test BaseSubscriber initialization."""
        subscriber = MinimalSubscriber()
        assert subscriber.metrics["processed_count"] == 0
        assert not subscriber.is_consuming

    async def test_pubsub_init(self) -> None:
        """Test RedisPubSub initialization."""
        with patch("src.common.pubsub._REDIS_AVAILABLE", True):
            pubsub = RedisPubSub()
            assert not pubsub.is_connected
            assert pubsub.active_subscriptions == set()

    async def test_circuit_breaker_call(self) -> None:
        """Test circuit breaker call functionality."""
        cb = CircuitBreaker(timeout=0.1)

        async def test_func() -> str:
            return "success"

        result = await cb.call(test_func)
        assert result == "success"
        assert cb.metrics["total_successes"] == 1

    async def test_global_cleanup(self) -> None:
        """Test global cleanup functions."""
        await cleanup_pubsub()  # Should not raise

    def test_redis_config_properties(self) -> None:
        """Test Redis config computed properties."""
        config = RedisConfig()

        assert config.redis_url == "redis://localhost:6379/0"
        assert config.is_development is True
        assert config.connection_pool_config["max_connections"] == 20

    async def test_subscriber_health_check(self) -> None:
        """Test subscriber health check."""
        subscriber = MinimalSubscriber()
        health = await subscriber.health_check()

        assert health["status"] == "stopped"
        assert "metrics" in health
