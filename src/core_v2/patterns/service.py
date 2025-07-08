"""Pattern: Service Class.

Version: 2025-07-08 (Initial - Pending Research)
ADR: ADR-002 (Pending)

Purpose: Define the canonical structure for business logic service classes
When to use: Any class that encapsulates business logic and coordinates operations
When NOT to use: For simple data containers (use Pydantic models) or pure utilities
"""

from abc import ABC, abstractmethod
from typing import Any


# CANONICAL IMPLEMENTATION
class BaseService(ABC):
    """Base service class establishing the standard interface and patterns.

    Key principles:
    - Dependency injection for testability
    - Async-first design
    - Clear separation of concerns
    - Comprehensive error handling
    """

    def __init__(self, db_session: Any, cache: Any | None = None):
        """Initialize with injected dependencies."""
        self.db = db_session
        self.cache = cache
        self._initialized = False

    async def initialize(self) -> None:
        """Async initialization hook for complex setup."""
        if self._initialized:
            return

        await self._setup()
        self._initialized = True

    @abstractmethod
    async def _setup(self) -> None:
        """Override for service-specific initialization."""
        pass

    async def health_check(self) -> dict[str, Any]:
        """Return standard health check data."""
        return {"service": self.__class__.__name__, "initialized": self._initialized, "status": "healthy"}


# USAGE EXAMPLE
class UserService(BaseService):
    """Example implementation following the pattern."""

    async def _setup(self) -> None:
        """Initialize user-specific resources."""
        # Example: warm up cache, verify DB schema, etc.
        pass

    async def get_by_id(self, user_id: int) -> dict[str, Any]:
        """Fetch user by ID with standard error handling."""
        # Check cache first
        if self.cache:
            cached = await self.cache.get(f"user:{user_id}")
            if cached:
                return cached  # type: ignore[no-any-return]

        # Fetch from database
        user = await self.db.fetch_one("SELECT * FROM users WHERE id = $1", user_id)

        if not user:
            raise ValueError(f"User {user_id} not found")

        # Cache for next time
        if self.cache:
            await self.cache.set(f"user:{user_id}", dict(user))

        return dict(user)


# TESTING APPROACH
"""
Test services using dependency injection:

async def test_user_service():
    # Mock dependencies
    mock_db = AsyncMock()
    mock_cache = AsyncMock()

    # Create service
    service = UserService(mock_db, mock_cache)
    await service.initialize()

    # Test behavior
    mock_db.fetch_one.return_value = {"id": 1, "name": "Test"}
    user = await service.get_by_id(1)

    assert user["name"] == "Test"
    mock_cache.set.assert_called_once()
"""

# MIGRATION NOTES
"""
To migrate existing services:
1. Extend BaseService instead of direct implementation
2. Move initialization logic to _setup() method
3. Add health_check() implementation
4. Ensure all methods are async
5. Use dependency injection for all external resources
"""

# TODO: Research and enhance this pattern with:
# - Advanced error handling strategies
# - Transaction management patterns
# - Retry/circuit breaker integration
# - Observability hooks (metrics, tracing)
# - Generic typing for better IDE support
