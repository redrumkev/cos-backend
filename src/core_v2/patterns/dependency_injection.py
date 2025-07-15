"""Pattern: Dependency Injection.

Version: 2025-07-11 (Initial - Needs Research)
ADR: ADR-002 (Living Patterns System)
Status: Not Yet Implemented - Placeholder for future development

Purpose: Define patterns for dependency injection and component wiring
When to use: Service initialization, component composition, testability
When NOT to use: Simple utilities or static functions
"""

from typing import Any, Protocol

# CANONICAL IMPLEMENTATION - PLACEHOLDER
# TODO: Research FastAPI dependency injection best practices
# - Look at FastAPI's own patterns
# - Study Stripe's API architecture
# - Review Google's Wire framework concepts


class ServiceProtocol(Protocol):
    """Base protocol for injectable services."""

    async def health_check(self) -> dict[str, Any]:
        """Required health check method."""
        ...


# USAGE EXAMPLE - PLACEHOLDER
"""
# In dependencies.py:
async def get_database() -> AsyncSession:
    async with async_session() as session:
        yield session

async def get_redis() -> Redis:
    return redis_client

async def get_user_service(
    db: Annotated[AsyncSession, Depends(get_database)],
    cache: Annotated[Redis, Depends(get_redis)]
) -> UserService:
    return UserService(db, cache)

# In router:
@router.get("/users/{id}")
async def get_user(
    user_id: int,
    service: Annotated[UserService, Depends(get_user_service)]
):
    return await service.get_by_id(user_id)
"""

# TESTING APPROACH - PLACEHOLDER
"""
# Override dependencies in tests:
app.dependency_overrides[get_database] = get_test_database
app.dependency_overrides[get_redis] = get_mock_redis
"""

# MIGRATION NOTES
"""
Current approach varies across modules. Need to:
1. Audit existing dependency patterns
2. Research best practices from leading projects
3. Define standard factory patterns
4. Create testing utilities for dependency mocking
5. Document lifecycle management patterns
"""

# TODO: Complete research and implementation
# Priority: HIGH - This pattern affects all service initialization
