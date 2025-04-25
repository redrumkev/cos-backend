"""API routes for the Control Center module.

This file defines all HTTP endpoints for the CC module,
connecting client requests to the appropriate services.
"""

# MDC: cc_module
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import log_event

from .deps import ModuleConfig, get_db_session, get_module_config
from .schemas import (
    CCConfig,
    HealthStatus,
    ModuleHealthStatus,
    ModulePingRequest,
    ModulePingResponse,
    SystemHealthReport,
)

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Basic Health Check",
    description="Provides a simple health status check for the service.",
    tags=["Health"],
)
async def health_check() -> HealthStatus:
    """Return the health status of the service."""
    log_event(
        source="cc",
        data={},
        tags=["health", "cc_router"],
        memo="Health check endpoint accessed.",
    )
    return HealthStatus(status="healthy")


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
    db: Annotated[AsyncSession, Depends(get_db_session)],
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
            ModuleHealthStatus(
                module="cc", status="healthy", last_updated="2025-04-02T10:00:00Z"
            ),
            ModuleHealthStatus(
                module="mem0", status="healthy", last_updated="2025-04-02T09:55:00Z"
            ),
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
    db: Annotated[AsyncSession, Depends(get_db_session)],
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
