"""Database operations for the Control Center module.

This file contains CRUD operations for interacting with the database,
using SQLAlchemy's async API for optimal performance.
"""

# MDC: cc_module
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import log_event

from .models import HealthStatus, Module


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

    stmt = select(HealthStatus).order_by(HealthStatus.last_updated.desc()).limit(1)
    result = await db.execute(stmt)
    return result.scalars().first()


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

    stmt = select(Module.name).where(Module.active == True)  # noqa: E712
    result = await db.execute(stmt)
    return list(result.scalars().all())


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

    module = Module(name=name, version=version, config=config)
    db.add(module)
    await db.commit()
    await db.refresh(module)
    return module


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

    stmt = select(Module).where(Module.id == module_id)
    result = await db.execute(stmt)
    return result.scalars().first()


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

    stmt = select(Module).where(Module.name == name)
    result = await db.execute(stmt)
    return result.scalars().first()


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

    stmt = select(Module).offset(skip).limit(limit).order_by(Module.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


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

    stmt = select(Module).where(Module.id == module_id)
    result = await db.execute(stmt)
    module = result.scalars().first()

    if module:
        for key, value in data.items():
            if hasattr(module, key):
                setattr(module, key, value)
        await db.commit()
        await db.refresh(module)

    return module


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

    stmt = select(Module).where(Module.id == module_id)
    result = await db.execute(stmt)
    module = result.scalars().first()

    if module:
        await db.delete(module)
        await db.commit()

    return module
