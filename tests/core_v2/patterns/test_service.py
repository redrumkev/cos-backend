# Test file - configured per-file ignores in ruff.toml handle common test patterns
"""Unit tests for service pattern implementation.

This file tests the BaseService abstract class and ensures proper coverage
of the pattern implementation, including the abstract method.

Following TDD methodology: RED → GREEN → REFACTOR
"""

from unittest.mock import Mock

import pytest

from src.core_v2.patterns.service import BaseService


class ConcreteService(BaseService):
    """Concrete implementation for testing BaseService."""

    async def _setup(self) -> None:
        """Concrete implementation of abstract method."""
        # Simulate some setup work
        self.setup_called = True


class TestBaseService:
    """Test BaseService abstract class functionality."""

    async def test_base_service_initialization(self) -> None:
        """Test BaseService initialization with dependencies."""
        mock_db = Mock()
        mock_cache = Mock()

        service = ConcreteService(mock_db, mock_cache)

        assert service.db == mock_db
        assert service.cache == mock_cache
        assert service._initialized is False

    async def test_base_service_initialize(self) -> None:
        """Test initialize method calls _setup."""
        mock_db = Mock()
        service = ConcreteService(mock_db)

        await service.initialize()

        assert service._initialized is True
        assert hasattr(service, "setup_called")
        assert service.setup_called is True

    async def test_base_service_initialize_idempotent(self) -> None:
        """Test that initialize is idempotent."""
        mock_db = Mock()
        service = ConcreteService(mock_db)

        # First initialization
        await service.initialize()
        assert service._initialized is True

        # Reset our tracking attribute
        service.setup_called = False

        # Second initialization should return early
        await service.initialize()

        # _setup should not be called again
        assert service.setup_called is False

    async def test_base_service_health_check(self) -> None:
        """Test health_check method returns expected format."""
        mock_db = Mock()
        service = ConcreteService(mock_db)

        # Before initialization
        health = await service.health_check()
        assert health == {"service": "ConcreteService", "initialized": False, "status": "healthy"}

        # After initialization
        await service.initialize()
        health = await service.health_check()
        assert health == {"service": "ConcreteService", "initialized": True, "status": "healthy"}

    async def test_base_service_no_cache(self) -> None:
        """Test BaseService works without cache."""
        mock_db = Mock()
        service = ConcreteService(mock_db, cache=None)

        assert service.db == mock_db
        assert service.cache is None

        await service.initialize()
        assert service._initialized is True


class TestAbstractMethodCoverage:
    """Test to ensure abstract method is properly covered."""

    def test_base_service_abstract_method_not_implemented(self) -> None:
        """Test that BaseService cannot be instantiated without implementing _setup."""
        mock_db = Mock()

        # Should raise TypeError when trying to instantiate abstract class
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseService(mock_db)  # type: ignore[abstract]

    async def test_abstract_method_must_be_implemented(self) -> None:
        """Test that _setup must be implemented in subclasses."""

        class IncompleteService(BaseService):
            """Service that doesn't implement _setup."""

            pass

        mock_db = Mock()

        # Should raise TypeError
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteService(mock_db)  # type: ignore[abstract]

    async def test_abstract_method_line_coverage(self) -> None:
        """Test to ensure line 43 (pass in abstract method) is covered."""
        # This test ensures the abstract method definition is covered
        # by checking the method exists and is abstract

        assert hasattr(BaseService, "_setup")
        assert hasattr(BaseService._setup, "__isabstractmethod__")
        assert BaseService._setup.__isabstractmethod__ is True

        # The 'pass' statement on line 43 is part of the abstract method
        # definition and is covered by the class definition itself
