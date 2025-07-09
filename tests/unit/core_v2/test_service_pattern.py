"""Comprehensive characterization tests for service.py pattern.

This module provides comprehensive testing for the BaseService pattern,
ensuring ≥95% coverage of all service lifecycle, dependency injection,
and integration scenarios.

Pattern Reference: service.py v2.1.0 (Living Patterns System)
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core_v2.patterns.service import BaseService, UserService


class TestBaseServicePattern:
    """Test BaseService pattern implementation and lifecycle."""

    def test_base_service_initialization(self) -> None:
        """Test BaseService initialization with dependencies."""
        # Test with both dependencies
        mock_db = MagicMock()
        mock_cache = MagicMock()

        class ConcreteService(BaseService):
            async def _setup(self) -> None:
                pass

        service = ConcreteService(mock_db, mock_cache)
        assert service.db is mock_db
        assert service.cache is mock_cache
        assert service._initialized is False

    def test_base_service_initialization_without_cache(self) -> None:
        """Test BaseService initialization without cache."""
        mock_db = MagicMock()

        class ConcreteService(BaseService):
            async def _setup(self) -> None:
                pass

        service = ConcreteService(mock_db)
        assert service.db is mock_db
        assert service.cache is None
        assert service._initialized is False

    async def test_initialize_method(self) -> None:
        """Test the initialize method lifecycle."""
        mock_db = MagicMock()
        setup_called = False

        class ConcreteService(BaseService):
            async def _setup(self) -> None:
                nonlocal setup_called
                setup_called = True

        service = ConcreteService(mock_db)

        # First initialization
        assert not service._initialized
        await service.initialize()
        assert service._initialized
        assert setup_called

    async def test_initialize_idempotency(self) -> None:
        """Test that initialize is idempotent."""
        mock_db = MagicMock()
        setup_count = 0

        class ConcreteService(BaseService):
            async def _setup(self) -> None:
                nonlocal setup_count
                setup_count += 1

        service = ConcreteService(mock_db)

        # Call initialize multiple times
        await service.initialize()
        await service.initialize()
        await service.initialize()

        # Setup should only be called once
        assert setup_count == 1
        assert service._initialized

    async def test_health_check_uninitialized(self) -> None:
        """Test health check on uninitialized service."""
        mock_db = MagicMock()

        class ConcreteService(BaseService):
            async def _setup(self) -> None:
                pass

        service = ConcreteService(mock_db)

        health = await service.health_check()

        assert health["service"] == "ConcreteService"
        assert health["initialized"] is False
        assert health["status"] == "healthy"

    async def test_health_check_initialized(self) -> None:
        """Test health check on initialized service."""
        mock_db = MagicMock()

        class ConcreteService(BaseService):
            async def _setup(self) -> None:
                pass

        service = ConcreteService(mock_db)
        await service.initialize()

        health = await service.health_check()

        assert health["service"] == "ConcreteService"
        assert health["initialized"] is True
        assert health["status"] == "healthy"

    async def test_abstract_setup_requirement(self) -> None:
        """Test that _setup must be implemented by concrete classes."""
        # This test verifies the abstract method requirement
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseService(MagicMock())  # type: ignore[abstract]


class TestUserServiceExample:
    """Test the UserService example implementation."""

    def test_user_service_inherits_base_service(self) -> None:
        """Test that UserService properly inherits from BaseService."""
        mock_db = MagicMock()
        service = UserService(mock_db)

        assert isinstance(service, BaseService)
        assert hasattr(service, "get_by_id")

    async def test_user_service_setup(self) -> None:
        """Test UserService _setup implementation."""
        mock_db = MagicMock()
        service = UserService(mock_db)

        # Should not raise any errors
        await service._setup()

        # Service can be initialized
        await service.initialize()
        assert service._initialized

    async def test_get_by_id_with_cache_hit(self) -> None:
        """Test get_by_id when user is in cache."""
        mock_db = AsyncMock()
        mock_cache = AsyncMock()

        # Setup cache hit
        cached_user = {"id": 1, "name": "Cached User"}
        mock_cache.get.return_value = cached_user

        service = UserService(mock_db, mock_cache)
        result = await service.get_by_id(1)

        # Should return cached user
        assert result == cached_user

        # Should check cache
        mock_cache.get.assert_called_once_with("user:1")

        # Should not hit database
        mock_db.fetch_one.assert_not_called()

    async def test_get_by_id_with_cache_miss(self) -> None:
        """Test get_by_id when user is not in cache."""
        mock_db = AsyncMock()
        mock_cache = AsyncMock()

        # Setup cache miss
        mock_cache.get.return_value = None

        # Setup database response
        db_user = {"id": 1, "name": "DB User"}
        mock_db.fetch_one.return_value = db_user

        service = UserService(mock_db, mock_cache)
        result = await service.get_by_id(1)

        # Should return database user
        assert result == db_user

        # Should check cache first
        mock_cache.get.assert_called_once_with("user:1")

        # Should query database
        mock_db.fetch_one.assert_called_once_with("SELECT * FROM users WHERE id = $1", 1)

        # Should cache the result
        mock_cache.set.assert_called_once_with("user:1", db_user)

    async def test_get_by_id_without_cache(self) -> None:
        """Test get_by_id when no cache is configured."""
        mock_db = AsyncMock()

        # Setup database response
        db_user = {"id": 1, "name": "DB User"}
        mock_db.fetch_one.return_value = db_user

        service = UserService(mock_db, cache=None)
        result = await service.get_by_id(1)

        # Should return database user
        assert result == db_user

        # Should query database
        mock_db.fetch_one.assert_called_once_with("SELECT * FROM users WHERE id = $1", 1)

    async def test_get_by_id_user_not_found(self) -> None:
        """Test get_by_id when user doesn't exist."""
        mock_db = AsyncMock()
        mock_cache = AsyncMock()

        # Setup cache miss
        mock_cache.get.return_value = None

        # Setup database to return None
        mock_db.fetch_one.return_value = None

        service = UserService(mock_db, mock_cache)

        with pytest.raises(ValueError, match="User 999 not found"):
            await service.get_by_id(999)

        # Should check cache
        mock_cache.get.assert_called_once_with("user:999")

        # Should query database
        mock_db.fetch_one.assert_called_once_with("SELECT * FROM users WHERE id = $1", 999)

        # Should not cache None result
        mock_cache.set.assert_not_called()

    async def test_get_by_id_cache_set_after_db_fetch(self) -> None:
        """Test that cache is properly set after database fetch."""
        mock_db = AsyncMock()
        mock_cache = AsyncMock()

        # Setup cache miss
        mock_cache.get.return_value = None

        # Setup database response with complex user object
        db_user = {
            "id": 42,
            "name": "Test User",
            "email": "test@example.com",
            "created_at": "2024-01-01",
            "metadata": {"preferences": {"theme": "dark"}},
        }
        mock_db.fetch_one.return_value = db_user

        service = UserService(mock_db, mock_cache)
        result = await service.get_by_id(42)

        # Verify result
        assert result == db_user

        # Verify cache was set with correct key and value
        mock_cache.set.assert_called_once_with("user:42", db_user)


class TestServicePatternRealWorldScenarios:
    """Test real-world service pattern scenarios."""

    async def test_service_with_multiple_dependencies(self) -> None:
        """Test service with multiple injected dependencies."""

        class ComplexService(BaseService):
            def __init__(
                self,
                db_session: Any,
                cache: Any | None = None,
                message_queue: Any | None = None,
                logger: Any | None = None,
            ):
                super().__init__(db_session, cache)
                self.message_queue = message_queue
                self.logger = logger

            async def _setup(self) -> None:
                if self.logger:
                    self.logger.info("Setting up ComplexService")

        mock_db = MagicMock()
        mock_cache = MagicMock()
        mock_mq = MagicMock()
        mock_logger = MagicMock()

        service = ComplexService(mock_db, mock_cache, mock_mq, mock_logger)
        await service.initialize()

        assert service.db is mock_db
        assert service.cache is mock_cache
        assert service.message_queue is mock_mq
        assert service.logger is mock_logger
        assert service._initialized

        # Verify logger was called during setup
        mock_logger.info.assert_called_once_with("Setting up ComplexService")

    async def test_service_error_handling_in_setup(self) -> None:
        """Test service behavior when _setup raises an error."""

        class FailingService(BaseService):
            async def _setup(self) -> None:
                raise RuntimeError("Setup failed")

        mock_db = MagicMock()
        service = FailingService(mock_db)

        # Initialize should propagate the error
        with pytest.raises(RuntimeError, match="Setup failed"):
            await service.initialize()

        # Service should not be marked as initialized
        assert not service._initialized

    async def test_service_concurrent_initialization(self) -> None:
        """Test service behavior with concurrent initialization attempts."""
        setup_count = 0
        setup_delay = 0.01

        class SlowSetupService(BaseService):
            async def _setup(self) -> None:
                nonlocal setup_count
                setup_count += 1
                await asyncio.sleep(setup_delay)

        mock_db = MagicMock()
        service = SlowSetupService(mock_db)

        # The base implementation allows concurrent setup calls if _initialized check
        # happens before the setup completes. This tests the actual behavior.
        tasks = [service.initialize() for _ in range(5)]
        await asyncio.gather(*tasks)

        # Without a lock, concurrent calls may all execute setup
        # This is the actual behavior of the current implementation
        assert setup_count >= 1  # At least one setup call
        assert service._initialized

    async def test_service_health_check_extension(self) -> None:
        """Test extending health check with custom data."""

        class ExtendedHealthService(BaseService):
            async def _setup(self) -> None:
                self.connection_count = 0

            async def health_check(self) -> dict[str, Any]:
                base_health = await super().health_check()
                base_health.update(
                    {
                        "connection_count": self.connection_count,
                        "cache_enabled": self.cache is not None,
                        "version": "1.0.0",
                    }
                )
                return base_health

        mock_db = MagicMock()
        mock_cache = MagicMock()

        service = ExtendedHealthService(mock_db, mock_cache)
        await service.initialize()

        health = await service.health_check()

        # Check base health data
        assert health["service"] == "ExtendedHealthService"
        assert health["initialized"] is True
        assert health["status"] == "healthy"

        # Check extended health data
        assert health["connection_count"] == 0
        assert health["cache_enabled"] is True
        assert health["version"] == "1.0.0"

    async def test_service_lifecycle_complete(self) -> None:
        """Test complete service lifecycle from creation to health check."""

        class LifecycleService(BaseService):
            def __init__(self, db_session: Any, cache: Any | None = None):
                super().__init__(db_session, cache)
                self.setup_completed = False

            async def _setup(self) -> None:
                # Simulate some setup work
                self.setup_completed = True

        # Create service
        mock_db = MagicMock()
        mock_cache = MagicMock()
        service = LifecycleService(mock_db, mock_cache)

        # Verify initial state
        assert not service._initialized
        assert not service.setup_completed

        # Initialize
        await service.initialize()

        # Verify initialized state
        assert service._initialized
        assert service.setup_completed

        # Check health
        health = await service.health_check()
        assert health["initialized"] is True
        assert health["status"] == "healthy"


class TestServicePatternDocumentation:
    """Test that the service pattern is well-documented."""

    def test_pattern_version_marker(self) -> None:
        """Test that the pattern has the correct version marker."""
        import src.core_v2.patterns.service

        docstring = src.core_v2.patterns.service.__doc__
        assert docstring is not None
        assert "Version: 2025-07-08" in docstring
        assert "ADR: ADR-002" in docstring

    def test_base_service_docstring(self) -> None:
        """Test that BaseService has comprehensive documentation."""
        docstring = BaseService.__doc__
        assert docstring is not None
        assert "Base service class" in docstring
        assert "Key principles:" in docstring
        assert "Dependency injection" in docstring
        assert "Async-first design" in docstring

    def test_user_service_example_docstring(self) -> None:
        """Test that UserService example has documentation."""
        docstring = UserService.__doc__
        assert docstring is not None
        assert "Example implementation" in docstring


# Run with: uv run pytest -n auto tests/unit/core_v2/test_service_pattern.py -v
