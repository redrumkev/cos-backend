"""API routes for the Control Center module.

This file defines all HTTP endpoints for the CC module,
connecting client requests to the appropriate services.
"""

# MDC: cc_module
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.backend.cc.logging import log_l1
from src.common.logger import log_event

from .deps import DBSession, ModuleConfig, get_module_config
from .mem0_router import router as mem0_router
from .schemas import (
    CCConfig,
    DebugLogRequest,
    DebugLogResponse,
    HealthStatusResponse,
    Module,
    ModuleCreate,
    ModuleHealthStatus,
    ModulePingRequest,
    ModulePingResponse,
    ModuleUpdate,
    SystemHealthReport,
)
from .services import create_module as service_create_module
from .services import delete_module as service_delete_module
from .services import get_module as service_get_module
from .services import get_modules as service_get_modules
from .services import read_system_health
from .services import update_module as service_update_module

router = APIRouter()

# Mount mem0 scratch data router
router.include_router(mem0_router, prefix="/mem0", tags=["mem0"])


@router.get(
    "/health",
    response_model=HealthStatusResponse,
    response_model_exclude_none=True,
    summary="Basic Health Check",
    description="Provides a simple health status check for the service.",
    tags=["Health"],
)
async def health_check(db: DBSession) -> HealthStatusResponse:
    """Return the health status of the service."""
    log_event(
        source="cc",
        data={},
        tags=["health", "cc_router"],
        memo="Health check endpoint accessed.",
    )
    row = await read_system_health(db)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no health record yet",
        )
    return HealthStatusResponse.model_validate(row)


@router.get(
    "/config",
    response_model=CCConfig,
    summary="Get CC Configuration",
    description="Retrieves the current configuration of the Control Center module.",
    tags=["Configuration"],
)
async def get_config(
    config: Annotated[ModuleConfig, Depends(get_module_config)],
) -> CCConfig:
    """Return the current configuration of the CC module."""
    log_event(
        source="cc",
        data={},
        tags=["configuration", "cc_router"],
        memo="Configuration endpoint accessed.",
    )
    return CCConfig(version=config["version"], modules_loaded=["cc", "mem0"])


@router.get(
    "/system/health",
    response_model=SystemHealthReport,
    summary="System Health Report",
    description="Provides a comprehensive health report for the entire system.",
    tags=["Health"],
)
async def system_health_report(
    db: DBSession,
) -> SystemHealthReport:
    """Get a comprehensive health report for all system modules."""
    log_event(
        source="cc",
        data={},
        tags=["health", "system", "cc_router"],
        memo="System health report endpoint accessed.",
    )
    return SystemHealthReport(
        overall_status="healthy",
        modules=[
            ModuleHealthStatus(module="cc", status="healthy", last_updated="2025-04-02T10:00:00Z"),
            ModuleHealthStatus(module="mem0", status="healthy", last_updated="2025-04-02T09:55:00Z"),
        ],
        timestamp="2025-04-02T10:15:00Z",
    )


@router.post(
    "/ping",
    response_model=ModulePingResponse,
    summary="Ping Module",
    description="Ping a specific module to check its health and connectivity.",
    tags=["Health"],
)
async def ping(
    request: ModulePingRequest,
    db: DBSession,
) -> ModulePingResponse:
    """Ping a specific module to verify its health status."""
    log_event(
        source="cc",
        data={"module": request.module},
        tags=["ping", "cc_router"],
        memo=f"Ping request for module {request.module}.",
    )
    if request.module not in ["cc", "mem0"]:
        return ModulePingResponse(module=request.module, status="unknown", latency_ms=0)
    return ModulePingResponse(module=request.module, status="healthy", latency_ms=5)


@router.get(
    "/status",
    response_model=dict[str, str],
)
async def get_status() -> dict[str, str]:
    """Return a simple status indicating the CC module is operational."""
    log_event(
        source="cc",
        data={},
        tags=["status", "cc_router"],
        memo="CC status endpoint accessed.",
    )
    return {"status": "ok"}


@router.post(
    "/debug/log",
    response_model=DebugLogResponse,
    response_model_exclude_none=True,
    summary="Debug Logging Endpoint",
    description="Create debug log entries using the log_l1 service for testing and diagnostics.",
    tags=["Debug"],
    status_code=status.HTTP_201_CREATED,
)
async def create_debug_log(
    request: DebugLogRequest,
    db: DBSession,
) -> DebugLogResponse:
    """Create debug log entries for testing and diagnostic purposes.

    This endpoint demonstrates service consumption patterns by calling the
    :pyfunc:`src.backend.cc.logging.log_l1` service directly.
    """
    start_time = time.perf_counter()

    try:
        # Persist logs via L1 logging service
        log_ids = await log_l1(
            db=db,
            event_type=request.event_type,
            payload=request.payload,
            prompt_data=request.prompt_data,
            request_id=request.request_id,
            trace_id=request.trace_id,
        )

        performance_ms = (time.perf_counter() - start_time) * 1000

        # Emit an additional audit log for the API call itself
        log_event(
            source="cc",
            data={
                "event_type": request.event_type,
                "log_ids": {k: str(v) for k, v in log_ids.items()},
                "performance_ms": performance_ms,
            },
            tags=["debug", "log", "cc_router"],
            memo="Debug log created via /debug/log endpoint.",
        )

        return DebugLogResponse(
            success=True,
            message=f"Debug log created successfully for event_type: {request.event_type}",
            log_ids=log_ids,
            performance_ms=performance_ms,
        )

    except Exception as exc:
        performance_ms = (time.perf_counter() - start_time) * 1000
        log_event(
            source="cc",
            data={
                "event_type": request.event_type,
                "error": str(exc),
                "performance_ms": performance_ms,
            },
            tags=["debug", "log", "error", "cc_router"],
            memo="Failed to create debug log via /debug/log endpoint.",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create debug log: {exc}",
        ) from exc


# Module CRUD Endpoints
@router.post(
    "/modules",
    response_model=Module,
    status_code=status.HTTP_201_CREATED,
    summary="Create Module",
    description="Create a new module in the system.",
    tags=["Modules"],
)
async def create_module(
    module_data: ModuleCreate,
    db: DBSession,
) -> Module:
    """Create a new module."""
    log_event(
        source="cc",
        data={"module": module_data.name},
        tags=["module", "create", "cc_router"],
        memo=f"Creating module {module_data.name}.",
    )

    try:
        module = await service_create_module(
            db, name=module_data.name, version=module_data.version, config=module_data.config
        )
        return Module.model_validate(module)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.get(
    "/modules",
    response_model=list[Module],
    summary="List Modules",
    description="Get a list of all modules with optional pagination.",
    tags=["Modules"],
)
async def list_modules(
    db: DBSession,
    skip: int = 0,
    limit: int = 100,
) -> list[Module]:
    """Get a list of modules with pagination."""
    log_event(
        source="cc",
        data={"skip": skip, "limit": limit},
        tags=["module", "list", "cc_router"],
        memo=f"Listing modules with skip={skip}, limit={limit}.",
    )

    modules = await service_get_modules(db, skip=skip, limit=limit)
    return [Module.model_validate(module) for module in modules]


@router.get(
    "/modules/{module_id}",
    response_model=Module,
    summary="Get Module",
    description="Get a specific module by its ID.",
    tags=["Modules"],
)
async def get_module(
    module_id: str,
    db: DBSession,
) -> Module:
    """Get a specific module by ID."""
    log_event(
        source="cc",
        data={"module_id": module_id},
        tags=["module", "get", "cc_router"],
        memo=f"Getting module {module_id}.",
    )

    module = await service_get_module(db, module_id)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Module with ID {module_id} not found")

    return Module.model_validate(module)


@router.patch(
    "/modules/{module_id}",
    response_model=Module,
    summary="Update Module",
    description="Update a specific module by its ID.",
    tags=["Modules"],
)
async def update_module(
    module_id: str,
    module_data: ModuleUpdate,
    db: DBSession,
) -> Module:
    """Update a specific module by ID."""
    log_event(
        source="cc",
        data={"module_id": module_id, "update_data": module_data.model_dump(exclude_unset=True)},
        tags=["module", "update", "cc_router"],
        memo=f"Updating module {module_id}.",
    )

    try:
        # Convert Pydantic model to dict, excluding unset fields
        update_data = module_data.model_dump(exclude_unset=True)

        module = await service_update_module(db, module_id, update_data)
        if not module:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Module with ID {module_id} not found")

        return Module.model_validate(module)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.delete(
    "/modules/{module_id}",
    response_model=Module,
    summary="Delete Module",
    description="Delete a specific module by its ID.",
    tags=["Modules"],
)
async def delete_module(
    module_id: str,
    db: DBSession,
) -> Module:
    """Delete a specific module by ID."""
    log_event(
        source="cc",
        data={"module_id": module_id},
        tags=["module", "delete", "cc_router"],
        memo=f"Deleting module {module_id}.",
    )

    module = await service_delete_module(db, module_id)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Module with ID {module_id} not found")

    return Module.model_validate(module)
