"""Database operations for the Control Center module.

This file contains CRUD operations for interacting with the database,
using SQLAlchemy's async API with modern database operations patterns.

Pattern Reference: src/core_v2/patterns/database_operations.py v2025-07-18
Applied: Repository pattern with BaseRepository for type-safe CRUD operations
Applied: Transaction context managers for automatic commit/rollback
Applied: Circuit breaker protection for database resilience
Applied: Modern SQLAlchemy 2.0+ patterns with proper session management
"""

# MDC: cc_module
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import log_event
from src.core_v2.patterns.database_operations import (
    BaseRepository,
    circuit_breaker,
    transactional,
)

from .models import HealthStatus, Module

# === REPOSITORY CLASSES (MODERN PATTERNS) ===


class HealthStatusRepository(BaseRepository[HealthStatus]):  # type: ignore[type-var]
    """Repository for HealthStatus operations with modern patterns."""

    async def get_latest(self) -> HealthStatus | None:
        """Get the most recent health status record."""
        stmt = select(HealthStatus).order_by(HealthStatus.last_updated.desc()).limit(1)
        result = await circuit_breaker.call(self.session.execute, stmt)
        return result.scalar_one_or_none()  # type: ignore[no-any-return]


class ModuleRepository(BaseRepository[Module]):  # type: ignore[type-var]
    """Repository for Module operations with modern patterns."""

    async def get_by_name(self, name: str) -> Module | None:
        """Get module by name."""
        stmt = select(Module).where(Module.name == name)
        result = await circuit_breaker.call(self.session.execute, stmt)
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def get_active_modules(self) -> list[str]:
        """Get list of active module names."""
        stmt = select(Module.name).where(Module.active == True)  # noqa: E712
        result = await circuit_breaker.call(self.session.execute, stmt)
        return list(result.scalars().all())

    async def create_with_defaults(self, name: str, version: str, config: str | None = None) -> Module:
        """Create module with explicit defaults for test environment."""
        from datetime import UTC, datetime

        # Use the parent create method but with explicit defaults
        return await self.create(
            name=name,
            version=version,
            config=config,
            active=True,
            last_active=datetime.now(UTC),
        )

    async def get_by_uuid(self, module_id: UUID) -> Module | None:
        """Get module by UUID string."""
        stmt = select(Module).where(Module.id == str(module_id))
        result = await circuit_breaker.call(self.session.execute, stmt)
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def update_by_uuid(self, module_id: UUID, data: dict[str, Any]) -> Module | None:
        """Update module by UUID with filtered data."""
        # Filter data to only include valid column names
        valid_columns = {"name", "version", "active", "config", "last_active"}
        filtered_data = {k: v for k, v in data.items() if k in valid_columns}

        if not filtered_data:
            # No valid fields to update, return the current module
            return await self.get_by_uuid(module_id)

        # Use UPDATE statement for better performance
        stmt = update(Module).where(Module.id == str(module_id)).values(**filtered_data).returning(Module)

        result = await circuit_breaker.call(self.session.execute, stmt)
        updated_instance = result.scalar_one_or_none()

        if updated_instance:
            await circuit_breaker.call(self.session.flush)

        return updated_instance  # type: ignore[no-any-return]

    async def delete_by_uuid(self, module_id: UUID) -> bool:
        """Delete module by UUID."""
        stmt = select(Module).where(Module.id == str(module_id))
        result = await circuit_breaker.call(self.session.execute, stmt)
        module = result.scalar_one_or_none()

        if module:
            await circuit_breaker.call(self.session.delete, module)
            return True
        return False


# === CONVENIENCE FUNCTIONS (BACKWARD COMPATIBILITY) ===


async def get_system_health(db: AsyncSession) -> HealthStatus | None:
    """Return the most recent HealthStatus row (or None).

    Args:
    ----
        db: AsyncSession: The database session

    Returns:
    -------
        Optional[HealthStatus]: Most recent health status record or None

    Example:
    -------
        ```python
        health_data = await get_system_health(db)
        ```

    """
    log_event(
        source="cc",
        data={},
        tags=["db", "health", "query"],
        memo="Querying system health from database",
    )

    # Use repository pattern for modern database operations
    repo = HealthStatusRepository(db, HealthStatus)
    return await repo.get_latest()


async def update_module_status(db: AsyncSession, module_name: str, status: str) -> dict[str, Any]:
    """Update health status for a specific module.

    Args:
    ----
        db: AsyncSession: The database session
        module_name: str: Name of the module to update
        status: str: New status to set

    Returns:
    -------
        dict[str, Any]: Updated status record

    Example:
    -------
        ```python
        updated = await update_module_status(db, "cc", "healthy")
        ```

    """
    log_event(
        source="cc",
        data={"module": module_name, "status": status},
        tags=["db", "health", "update"],
        memo=f"Updating status for module {module_name} to {status}",
    )

    # Placeholder implementation - will update health_status table once implemented
    # stmt = (
    #     update(HealthStatus)
    #     .where(HealthStatus.module == module_name)
    #     .values(status=status, last_updated=datetime.utcnow())
    #     .returning(HealthStatus)
    # )
    # result = await db.execute(stmt)
    # await db.commit()
    # return result.scalar_one()

    # Return mock response for now
    return {
        "module": module_name,
        "status": status,
        "last_updated": "2025-04-02T10:10:00Z",
    }


async def get_active_modules(db: AsyncSession) -> list[str]:
    """Get a list of all active modules in the system.

    Args:
    ----
        db: AsyncSession: The database session

    Returns:
    -------
        list[str]: List of active module names

    Example:
    -------
        ```python
        modules = await get_active_modules(db)
        ```

    """
    log_event(
        source="cc",
        data={},
        tags=["db", "modules", "query"],
        memo="Querying active modules from database",
    )

    # Use repository pattern for modern database operations
    repo = ModuleRepository(db, Module)
    return await repo.get_active_modules()


# Module CRUD Operations
async def create_module(db: AsyncSession, name: str, version: str, config: str | None = None) -> Module:
    """Create a new module record.

    Args:
    ----
        db: AsyncSession: The database session
        name: str: Name of the module
        version: str: Version of the module
        config: str | None: Optional JSON configuration string

    Returns:
    -------
        Module: The created module record

    Example:
    -------
        ```python
        module = await create_module(db, "new_module", "1.0.0")
        ```

    """
    log_event(
        source="cc",
        data={"name": name, "version": version},
        tags=["db", "module", "create"],
        memo=f"Creating new module {name} version {version}",
    )

    # Use repository pattern with transaction context manager
    repo = ModuleRepository(db, Module)
    async with transactional(db) as tx_session:
        repo.session = tx_session  # Update repository session to transaction session
        return await repo.create_with_defaults(name, version, config)


async def get_module(db: AsyncSession, module_id: str) -> Module | None:
    """Get a module by its ID.

    Args:
    ----
        db: AsyncSession: The database session
        module_id: str: UUID of the module

    Returns:
    -------
        Module | None: The module record or None if not found

    Example:
    -------
        ```python
        module = await get_module(db, "123e4567-e89b-12d3-a456-426614174000")
        ```

    """
    log_event(
        source="cc",
        data={"module_id": module_id},
        tags=["db", "module", "read"],
        memo=f"Retrieving module {module_id}",
    )

    # Use repository pattern for modern database operations
    repo = ModuleRepository(db, Module)
    uuid_obj = UUID(module_id)
    return await repo.get_by_uuid(uuid_obj)


async def get_module_by_name(db: AsyncSession, name: str) -> Module | None:
    """Get a module by its name.

    Args:
    ----
        db: AsyncSession: The database session
        name: str: Name of the module

    Returns:
    -------
        Module | None: The module record or None if not found

    Example:
    -------
        ```python
        module = await get_module_by_name(db, "cc")
        ```

    """
    log_event(
        source="cc",
        data={"name": name},
        tags=["db", "module", "read"],
        memo=f"Retrieving module by name {name}",
    )

    # Use repository pattern for modern database operations
    repo = ModuleRepository(db, Module)
    return await repo.get_by_name(name)


async def get_modules(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Module]:
    """Get a list of modules with pagination.

    Args:
    ----
        db: AsyncSession: The database session
        skip: int: Number of records to skip
        limit: int: Maximum number of records to return

    Returns:
    -------
        list[Module]: List of module records

    Example:
    -------
        ```python
        modules = await get_modules(db, skip=0, limit=10)
        ```

    """
    log_event(
        source="cc",
        data={"skip": skip, "limit": limit},
        tags=["db", "module", "read"],
        memo=f"Retrieving modules with skip={skip}, limit={limit}",
    )

    # Use repository pattern for modern database operations
    repo = ModuleRepository(db, Module)
    return await repo.list_all(offset=skip, limit=limit, order_by=Module.name)


async def update_module(db: AsyncSession, module_id: str, data: dict[str, Any]) -> Module | None:
    """Update a module record.

    Args:
    ----
        db: AsyncSession: The database session
        module_id: str: UUID of the module
        data: dict[str, Any]: Dictionary of fields to update

    Returns:
    -------
        Module | None: The updated module record or None if not found

    Example:
    -------
        ```python
        updated = await update_module(db, "123e4567-e89b-12d3-a456-426614174000", {"version": "1.1.0"})
        ```

    """
    log_event(
        source="cc",
        data={"module_id": module_id, "update_data": data},
        tags=["db", "module", "update"],
        memo=f"Updating module {module_id}",
    )

    # Use repository pattern with transaction context manager
    repo = ModuleRepository(db, Module)
    uuid_obj = UUID(module_id)

    async with transactional(db) as tx_session:
        repo.session = tx_session  # Update repository session to transaction session
        return await repo.update_by_uuid(uuid_obj, data)


async def delete_module(db: AsyncSession, module_id: str) -> Module | None:
    """Delete a module record.

    Args:
    ----
        db: AsyncSession: The database session
        module_id: str: UUID of the module

    Returns:
    -------
        Module | None: The deleted module record or None if not found

    Example:
    -------
        ```python
        deleted = await delete_module(db, "123e4567-e89b-12d3-a456-426614174000")
        ```

    """
    log_event(
        source="cc",
        data={"module_id": module_id},
        tags=["db", "module", "delete"],
        memo=f"Deleting module {module_id}",
    )

    # Use repository pattern with transaction context manager
    repo = ModuleRepository(db, Module)
    uuid_obj = UUID(module_id)

    async with transactional(db) as tx_session:
        repo.session = tx_session  # Update repository session to transaction session

        # Get the module before deletion
        module = await repo.get_by_uuid(uuid_obj)
        if module:
            await repo.delete_by_uuid(uuid_obj)
        return module
