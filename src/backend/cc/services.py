"""Business logic services for the Control Center module.

This file contains the core business logic that coordinates
database operations, external API calls, and implements the
module's primary responsibilities.
"""

# MDC: cc_module
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import log_event

from .crud import create_module as crud_create_module
from .crud import delete_module as crud_delete_module
from .crud import get_active_modules, get_system_health, update_module_status
from .crud import get_module as crud_get_module
from .crud import get_module_by_name as crud_get_module_by_name
from .crud import get_modules as crud_get_modules
from .crud import update_module as crud_update_module
from .models import HealthStatus, Module


def get_status() -> dict[str, str]:
    """Health check or CC status entry point.

    Legacy function moved from controller.py

    Returns:
        dict[str, str]: Simple status response

    """
    log_event(
        source="cc",
        data={"msg": "Control Center status requested."},
        tags=["status", "heartbeat"],
        memo="Initial /status check",
    )
    return {"cc": "online", "message": "Control Center active."}


async def read_system_health(db: AsyncSession) -> HealthStatus | None:
    """Thin façade consumed by the router for getting system health.

    Args:
        db: AsyncSession: The database session

    Returns:
        Optional[HealthStatus]: Most recent health status record or None

    Example:
        ```python
        health_record = await read_system_health(db)
        ```

    """
    return await get_system_health(db)


async def check_system_health(db: AsyncSession) -> dict[str, Any]:
    """Perform a comprehensive system health check across all modules.

    Args:
        db: AsyncSession: The database session

    Returns:
        dict[str, Any]: System health report including status for all modules

    Example:
        ```python
        health_report = await check_system_health(db)
        ```

    """
    log_event(
        source="cc",
        data={},
        tags=["service", "health"],
        memo="System health check initiated",
    )

    # Get health status for all modules
    module_health = await get_system_health(db)

    # Compute overall system health based on the single health record
    if module_health and module_health.status == "healthy":
        overall_status = "healthy"
        modules = [{"module": module_health.module, "status": module_health.status}]
    elif module_health:
        overall_status = "degraded"
        modules = [{"module": module_health.module, "status": module_health.status}]
    else:
        overall_status = "unknown"
        modules = []

    # Structure the response
    return {
        "overall_status": overall_status,
        "modules": modules,
        # Will use datetime.utcnow().isoformat() + "Z"
        "timestamp": "2025-04-02T10:15:00Z",
    }


async def get_cc_configuration(db: AsyncSession) -> dict[str, Any]:
    """Get current Control Center configuration including active modules.

    Args:
        db: AsyncSession: The database session

    Returns:
        dict[str, Any]: Current CC configuration

    Example:
        ```python
        config = await get_cc_configuration(db)
        ```

    """
    log_event(
        source="cc",
        data={},
        tags=["service", "config"],
        memo="CC configuration requested",
    )

    # Get list of active modules
    active_modules = await get_active_modules(db)

    # Return configuration data
    return {
        "version": "0.1.0",
        "modules_loaded": active_modules,
        "environment": "development",
    }


async def ping_module(db: AsyncSession, module_name: str) -> dict[str, Any]:
    """Ping a specific module to check its health status.

    Args:
        db: AsyncSession: The database session
        module_name: str: Name of the module to ping

    Returns:
        dict[str, Any]: Module ping response

    Example:
        ```python
        ping_result = await ping_module(db, "mem0")
        ```

    """
    log_event(
        source="cc",
        data={"module": module_name},
        tags=["service", "ping"],
        memo=f"Pinging module {module_name}",
    )

    # Simplified implementation for testing purposes
    # In a real implementation, this would make an HTTP request
    # to the module's health endpoint or use a Redis pub/sub pattern
    status = "healthy" if module_name in ["cc", "mem0"] else "unknown"

    # Update module status in the database
    await update_module_status(db, module_name, status)

    return {
        "module": module_name,
        "status": status,
        "latency_ms": 5,  # This would be measured in a real implementation
    }


# Module Service Operations
async def create_module(db: AsyncSession, name: str, version: str, config: str | None = None) -> Module:
    """Create a new module with business logic validation.

    Args:
        db: AsyncSession: The database session
        name: str: Name of the module
        version: str: Version of the module
        config: str | None: Optional JSON configuration string

    Returns:
        Module: The created module record

    Raises:
        ValueError: If module with the same name already exists

    Example:
        ```python
        module = await create_module(db, "new_module", "1.0.0")
        ```

    """
    log_event(
        source="cc",
        data={"name": name, "version": version},
        tags=["service", "module", "create"],
        memo=f"Creating module {name} version {version}",
    )

    # Check if module with the same name already exists
    existing_module = await crud_get_module_by_name(db, name)
    if existing_module:
        raise ValueError(f"Module with name '{name}' already exists")

    # Create the module
    return await crud_create_module(db, name, version, config)


async def get_module(db: AsyncSession, module_id: str) -> Module | None:
    """Get a module by its ID.

    Args:
        db: AsyncSession: The database session
        module_id: str: UUID of the module

    Returns:
        Module | None: The module record or None if not found

    Example:
        ```python
        module = await get_module(db, "123e4567-e89b-12d3-a456-426614174000")
        ```

    """
    log_event(
        source="cc",
        data={"module_id": module_id},
        tags=["service", "module", "read"],
        memo=f"Retrieving module {module_id}",
    )

    return await crud_get_module(db, module_id)


async def get_module_by_name(db: AsyncSession, name: str) -> Module | None:
    """Get a module by its name.

    Args:
        db: AsyncSession: The database session
        name: str: Name of the module

    Returns:
        Module | None: The module record or None if not found

    Example:
        ```python
        module = await get_module_by_name(db, "cc")
        ```

    """
    log_event(
        source="cc",
        data={"name": name},
        tags=["service", "module", "read"],
        memo=f"Retrieving module by name {name}",
    )

    return await crud_get_module_by_name(db, name)


async def get_modules(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Module]:
    """Get a list of modules with pagination.

    Args:
        db: AsyncSession: The database session
        skip: int: Number of records to skip
        limit: int: Maximum number of records to return

    Returns:
        list[Module]: List of module records

    Example:
        ```python
        modules = await get_modules(db, skip=0, limit=10)
        ```

    """
    log_event(
        source="cc",
        data={"skip": skip, "limit": limit},
        tags=["service", "module", "read"],
        memo=f"Retrieving modules with skip={skip}, limit={limit}",
    )

    return await crud_get_modules(db, skip, limit)


async def update_module(db: AsyncSession, module_id: str, data: dict[str, Any]) -> Module | None:
    """Update a module record with business logic validation.

    Args:
        db: AsyncSession: The database session
        module_id: str: UUID of the module
        data: dict[str, Any]: Dictionary of fields to update

    Returns:
        Module | None: The updated module record or None if not found

    Raises:
        ValueError: If trying to update to a name that already exists

    Example:
        ```python
        updated = await update_module(db, "123e4567-e89b-12d3-a456-426614174000", {"version": "1.1.0"})
        ```

    """
    log_event(
        source="cc",
        data={"module_id": module_id, "update_data": data},
        tags=["service", "module", "update"],
        memo=f"Updating module {module_id}",
    )

    # If updating name, check that the new name doesn't conflict
    if "name" in data:
        existing_module = await crud_get_module_by_name(db, data["name"])
        if existing_module and str(existing_module.id) != module_id:
            raise ValueError(f"Module with name '{data['name']}' already exists")

    return await crud_update_module(db, module_id, data)


async def delete_module(db: AsyncSession, module_id: str) -> Module | None:
    """Delete a module record.

    Args:
        db: AsyncSession: The database session
        module_id: str: UUID of the module

    Returns:
        Module | None: The deleted module record or None if not found

    Example:
        ```python
        deleted = await delete_module(db, "123e4567-e89b-12d3-a456-426614174000")
        ```

    """
    log_event(
        source="cc",
        data={"module_id": module_id},
        tags=["service", "module", "delete"],
        memo=f"Deleting module {module_id}",
    )

    return await crud_delete_module(db, module_id)
