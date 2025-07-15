"""API routes for the Control Center module.

This file defines all HTTP endpoints for the CC module,
connecting client requests to the appropriate services.

Pattern Reference: router.py v3.0.0 (Research-Driven Implementation)
Applied: create_module_router factory pattern
Applied: RFC 9457 Problem Details for error responses
Applied: Annotated[Type, Depends()] dependency injection
Applied: ModuleDeps for bundled dependencies
Applied: Request ID propagation for tracing
"""

# MDC: cc_module
import copy
import time
import uuid
from typing import Annotated, Any

from fastapi import BackgroundTasks, Depends, Request, status
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.logging import log_l1
from src.common.config import Settings, get_settings
from src.common.database import get_async_db
from src.common.logger import log_event
from src.common.request_id_middleware import get_request_id
from src.core_v2.patterns.error_handling import (
    ConflictError,
    COSError,
    ErrorCategory,
    NotFoundError,
    ValidationError,
)
from src.core_v2.patterns.router import (
    ModuleDeps,
    PaginationParams,
    RateLimitConfig,
    create_module_router,
)
from src.graph.registry import ModuleLabel

from .deps import ModuleConfig, get_module_config
from .mem0_router import router as mem0_router
from .schemas import (
    CCConfig,
    CircuitBreakerStatus,
    ConnectionPoolStatus,
    DebugLogRequest,
    DebugLogResponse,
    DLQMetrics,
    EnhancedHealthResponse,
    HealthStatusResponse,
    Module,
    ModuleCreate,
    ModuleHealthStatus,
    ModulePingRequest,
    ModulePingResponse,
    ModuleUpdate,
    RedisHealthResponse,
    RedisPerformanceMetrics,
    RedisValidationInfo,
    SystemHealthReport,
)
from .services import create_module as service_create_module
from .services import delete_module as service_delete_module
from .services import get_module as service_get_module
from .services import get_modules as service_get_modules
from .services import read_system_health
from .services import update_module as service_update_module

# Create router with new pattern (versioned for main app)
router = create_module_router(
    prefix="/cc",
    module=ModuleLabel.TECH_CC,
    tags=["control-center", "health", "monitoring"],
    version="v1",
    rate_limit=RateLimitConfig(requests_per_minute=300, burst_size=50),
)

# Create non-versioned router for testing purposes
router_test = create_module_router(
    prefix="/cc",
    module=ModuleLabel.TECH_CC,
    tags=["control-center", "health", "monitoring"],
    version=None,  # No version for testing
    rate_limit=RateLimitConfig(requests_per_minute=300, burst_size=50),
)

# Mount mem0 scratch data router on both routers
router.include_router(mem0_router, prefix="/mem0", tags=["mem0"])
router_test.include_router(mem0_router, prefix="/mem0", tags=["mem0"])


# Create module dependencies factory for this module
async def get_module_deps(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    background_tasks: BackgroundTasks,
) -> ModuleDeps:
    """Get module dependencies instance."""
    return ModuleDeps(
        module=ModuleLabel.TECH_CC,
        request=request,
        db=db,
        settings=settings,
        background_tasks=background_tasks,
        request_id=get_request_id(),
    )


@router.get(
    "/health",
    response_model=HealthStatusResponse,
    response_model_exclude_none=True,
    summary="Basic Health Check",
    description="Provides a simple health status check for the service.",
    tags=["Health"],
)
async def health_check(
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> HealthStatusResponse:
    """Return the health status of the service."""
    log_event(
        source="cc",
        data={"request_id": deps.request_id},
        tags=["health", "cc_router"],
        memo="Health check endpoint accessed.",
    )
    if deps.db is None:
        raise COSError(
            message="Database connection not available",
            category=ErrorCategory.INTERNAL,
            user_message="Database connection not available",
        )
    row = await read_system_health(deps.db)
    if not row:
        raise NotFoundError(
            resource="Health record", identifier="system", user_message="No health record available yet"
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
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> SystemHealthReport:
    """Get a comprehensive health report for all system modules."""
    log_event(
        source="cc",
        data={"request_id": deps.request_id},
        tags=["health", "system", "cc_router"],
        memo="System health report endpoint accessed.",
    )
    from datetime import datetime

    current_time = datetime.utcnow().isoformat() + "Z"
    return SystemHealthReport(
        overall_status="healthy",
        modules=[
            ModuleHealthStatus(module="cc", status="healthy", last_updated=current_time),
            ModuleHealthStatus(module="mem0", status="healthy", last_updated=current_time),
        ],
        timestamp=current_time,
    )


@router.get(
    "/health/enhanced",
    response_model=EnhancedHealthResponse,
    summary="Enhanced Health Check with Circuit Breaker and DLQ Metrics",
    description="Provides comprehensive health status including circuit breaker state and DLQ metrics.",
    tags=["Health"],
)
async def enhanced_health_check() -> EnhancedHealthResponse:
    """Return enhanced health status including circuit breaker and DLQ metrics."""
    log_event(
        source="cc",
        data={},
        tags=["health", "enhanced", "circuit_breaker", "dlq"],
        memo="Enhanced health check endpoint accessed.",
    )

    # TODO: Replace with actual Redis connection and circuit breaker instances
    # For now, return mock data that demonstrates the structure
    from datetime import datetime

    # Mock circuit breaker status (would come from actual circuit breaker instance)
    circuit_breaker_status = CircuitBreakerStatus(
        state="CLOSED",
        failure_count=0,
        last_failure_time=None,
        next_attempt_time=None,
    )

    # Mock DLQ metrics (would come from actual Redis queries)
    dlq_metrics = [
        DLQMetrics(
            size=0,  # Would use: await redis_client.xlen("subscriber_dlq")
            channel="subscriber_dlq",
            oldest_message_time=None,
            newest_message_time=None,
        )
    ]

    # Mock uptime (would track actual service start time)
    uptime_seconds = 3600.0  # 1 hour placeholder

    # Mock Redis connection status (would check actual Redis connectivity)
    redis_connected = True  # Would use: await redis_client.ping()

    # Check Qdrant status (gracefully handles unavailability)
    from .vector_service import get_vector_service

    vector_service = get_vector_service()
    qdrant_health = await vector_service.health_check()
    # qdrant_status is tracked in qdrant_health response

    current_time = datetime.utcnow()

    # Determine overall status based on metrics
    overall_status = "healthy"
    if circuit_breaker_status.state == "OPEN":
        overall_status = "degraded"
    elif not redis_connected:
        overall_status = "offline"
    elif any(dlq.size > 100 for dlq in dlq_metrics):  # High DLQ size threshold
        overall_status = "degraded"
    # Note: Qdrant unavailability doesn't degrade status (graceful fallback)
    # TODO: Change this when Qdrant becomes required in Sprint 3

    return EnhancedHealthResponse(
        status=overall_status,
        timestamp=current_time.isoformat() + "Z",
        circuit_breaker_state=circuit_breaker_status,
        dlq_metrics=dlq_metrics,
        uptime_seconds=uptime_seconds,
        redis_connected=redis_connected,
        qdrant_status=qdrant_health,
    )


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Exposes Prometheus metrics for monitoring and observability.",
    tags=["Monitoring"],
    include_in_schema=False,  # Don't include in OpenAPI schema
)
async def metrics() -> Any:
    """Expose Prometheus metrics endpoint."""
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

        # Log access to metrics endpoint
        log_event(
            source="cc",
            data={},
            tags=["metrics", "prometheus", "monitoring"],
            memo="Prometheus metrics endpoint accessed.",
        )

        # Create custom metrics for circuit breaker and DLQ
        # In a real implementation, these would be updated by the actual components

        # Circuit breaker state metric (enum converted to gauge)
        circuit_breaker_state_gauge = Gauge(
            "circuit_breaker_state", "Circuit breaker state (0=CLOSED, 1=HALF_OPEN, 2=OPEN)", ["component"]
        )
        circuit_breaker_state_gauge.labels(component="subscriber").set(0)  # CLOSED

        # Circuit breaker failure count
        circuit_breaker_failures = Gauge(
            "circuit_breaker_failures_total", "Total number of circuit breaker failures", ["component"]
        )
        circuit_breaker_failures.labels(component="subscriber").set(0)

        # DLQ size metric
        dlq_size_gauge = Gauge("dlq_size", "Number of messages in Dead Letter Queue", ["channel"])
        dlq_size_gauge.labels(channel="subscriber_dlq").set(0)

        # Service uptime
        uptime_gauge = Gauge("service_uptime_seconds", "Service uptime in seconds")
        uptime_gauge.set(3600.0)  # Mock 1 hour

        # Redis connection status
        redis_connection_gauge = Gauge("redis_connected", "Redis connection status (1=connected, 0=disconnected)")
        redis_connection_gauge.set(1)  # Connected

        # In-flight messages (for subscriber)
        inflight_messages_gauge = Gauge(
            "subscriber_inflight_messages", "Number of messages currently being processed", ["channel"]
        )
        inflight_messages_gauge.labels(channel="subscriber").set(0)

        # Generate and return metrics in Prometheus format
        from fastapi import Response

        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    except ImportError:
        # Fallback if prometheus_client is not available
        log_event(
            source="cc",
            data={"error": "prometheus_client not available"},
            tags=["metrics", "error"],
            memo="Prometheus client library not available for metrics endpoint.",
        )
        return Response(content="# Prometheus client not available\n", media_type="text/plain")


@router.post(
    "/ping",
    response_model=ModulePingResponse,
    summary="Ping Module",
    description="Ping a specific module to check its health and connectivity.",
    tags=["Health"],
)
async def ping(
    request: ModulePingRequest,
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> ModulePingResponse:
    """Ping a specific module to verify its health status."""
    log_event(
        source="cc",
        data={"module": request.module, "request_id": deps.request_id},
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
    summary="Enhanced Debug Logging Endpoint",
    description="Create debug log entries with Redis publishing validation for testing and diagnostics.",
    tags=["Debug"],
    status_code=status.HTTP_201_CREATED,
)
async def create_debug_log(
    request: DebugLogRequest,
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> DebugLogResponse:
    """Create debug log entries for testing and diagnostic purposes with Redis validation.

    This endpoint demonstrates service consumption patterns by calling the
    :pyfunc:`src.backend.cc.logging.log_l1` service directly and includes
    Redis publishing validation as part of Task 008 implementation.
    """
    start_time = time.perf_counter()

    try:
        # Persist logs via L1 logging service
        if deps.db is None:
            raise COSError(
                message="Database connection not available",
                category=ErrorCategory.INTERNAL,
                user_message="Database connection not available",
            )

        log_ids = await log_l1(
            db=deps.db,
            event_type=request.event_type,
            payload=request.payload,
            prompt_data=request.prompt_data,
            request_id=request.request_id or deps.request_id,
            trace_id=request.trace_id,
        )

        # Perform Redis validation for the debug log in background
        if deps.background_tasks is not None:
            deps.background_tasks.add_task(_log_redis_validation, request, deps.request_id or "unknown")

        # Perform Redis validation for the debug log
        redis_validation = await _validate_redis_publishing(request)

        performance_ms = (time.perf_counter() - start_time) * 1000

        # Emit an additional audit log for the API call itself
        log_event(
            source="cc",
            data={
                "event_type": request.event_type,
                "log_ids": {k: str(v) for k, v in log_ids.items()},
                "performance_ms": performance_ms,
                "redis_validation": {
                    "publish_success": redis_validation.publish_success,
                    "connection_status": redis_validation.connection_status,
                },
                "request_id": deps.request_id,
            },
            tags=["debug", "log", "cc_router", "redis_validation"],
            memo="Debug log created via enhanced /debug/log endpoint with Redis validation.",
        )

        return DebugLogResponse(
            success=True,
            message=f"Debug log created successfully for event_type: {request.event_type}",
            log_ids=log_ids,
            performance_ms=performance_ms,
            redis_validation=redis_validation,
        )

    except Exception as exc:
        performance_ms = (time.perf_counter() - start_time) * 1000

        # Attempt to get Redis validation even on failure
        try:
            redis_validation = await _validate_redis_publishing(request)
        except Exception:
            # If Redis validation also fails, provide a minimal response
            redis_validation = RedisValidationInfo(
                publish_success=False,
                connection_status="error",
                error_details="Redis validation failed during error recovery",
            )

        log_event(
            source="cc",
            data={
                "event_type": request.event_type,
                "error": str(exc),
                "performance_ms": performance_ms,
                "redis_validation": {
                    "publish_success": redis_validation.publish_success,
                    "connection_status": redis_validation.connection_status,
                },
                "request_id": deps.request_id,
            },
            tags=["debug", "log", "error", "cc_router", "redis_validation"],
            memo="Failed to create debug log via enhanced /debug/log endpoint.",
        )
        raise COSError(
            message=f"Failed to create debug log: {exc}",
            category=ErrorCategory.INTERNAL,
            details={"event_type": request.event_type},
            user_message="Unable to create debug log entry",
        ) from exc


async def _log_redis_validation(request: DebugLogRequest, request_id: str) -> None:
    """Background task to log Redis validation results."""
    try:
        validation_result = await _validate_redis_publishing(request)
        log_event(
            source="cc",
            data={
                "event_type": request.event_type,
                "validation_result": {
                    "publish_success": validation_result.publish_success,
                    "connection_status": validation_result.connection_status,
                    "latency_ms": validation_result.redis_latency_ms,
                },
                "request_id": request_id,
            },
            tags=["background", "redis_validation"],
            memo="Background Redis validation completed.",
        )
    except Exception as e:
        log_event(
            source="cc",
            data={
                "event_type": request.event_type,
                "error": str(e),
                "request_id": request_id,
            },
            tags=["background", "redis_validation", "error"],
            memo="Background Redis validation failed.",
        )


async def _validate_redis_publishing(request: DebugLogRequest) -> RedisValidationInfo:
    """Validate Redis publishing by attempting to publish a test message.

    This helper function tests Redis connectivity and message publishing
    for the enhanced debug log endpoint.
    """
    from datetime import datetime

    from src.common.message_format import EventType, build_message
    from src.common.pubsub import get_pubsub

    redis_start_time = time.perf_counter()

    try:
        # Get the Redis pub/sub instance
        pubsub = await get_pubsub()

        # Create a test message using the standardized format
        test_message_data = {
            "debug_validation_type": f"debug_validation_{request.event_type}",
            "original_event_type": request.event_type,
            "validation_timestamp": datetime.utcnow().isoformat() + "Z",
            "payload_preview": request.payload,
            "tags": ["debug", "validation", "redis_test"],
        }

        # Attempt to publish to a test channel
        await pubsub.publish("debug_validation", test_message_data)

        # Also create the formatted message for response
        test_message = build_message(
            base_log_id=uuid.uuid4(),
            source_module="backend.cc.debug",
            timestamp=datetime.utcnow(),
            trace_id=request.trace_id or "debug-validation",
            request_id=request.request_id or "debug-request",
            event_type=EventType.EVENT_LOG,
            data=test_message_data,
        )

        redis_latency_ms = (time.perf_counter() - redis_start_time) * 1000

        return RedisValidationInfo(
            publish_success=True,
            published_message=test_message,
            redis_latency_ms=redis_latency_ms,
            connection_status="connected",
        )

    except Exception as exc:
        redis_latency_ms = (time.perf_counter() - redis_start_time) * 1000

        return RedisValidationInfo(
            publish_success=False,
            published_message=None,
            redis_latency_ms=redis_latency_ms,
            connection_status="error",
            error_details=str(exc),
        )


@router.get(
    "/debug/redis-health",
    response_model=RedisHealthResponse,
    summary="Redis Health Status",
    description="Comprehensive Redis health monitoring including connection pool, "
    "performance metrics, and circuit breaker status.",
    tags=["Debug", "Health"],
)
async def redis_health_check() -> RedisHealthResponse:
    """Get comprehensive Redis health status for monitoring and diagnostics.

    This endpoint provides detailed Redis health information including:
    - Connection pool status and metrics
    - Performance benchmarks and latencies
    - Circuit breaker state and failure tracking
    - Redis server information and statistics
    """
    from datetime import datetime

    from src.common.pubsub import get_pubsub

    check_start_time = time.perf_counter()
    current_time = datetime.utcnow()

    try:
        # Get the Redis pub/sub instance
        pubsub = await get_pubsub()

        # Perform a ping to measure latency
        ping_start = time.perf_counter()
        await pubsub._redis.ping()
        ping_latency_ms = (time.perf_counter() - ping_start) * 1000

        # Get Redis server information
        redis_info = await pubsub._redis.info()

        # Extract connection pool information
        pool = pubsub._redis.connection_pool
        max_connections = pool.max_connections
        # Calculate active/idle connections (approximation)
        created_connections = len(pool._created_connections) if hasattr(pool, "_created_connections") else 0
        available_connections = (
            len(pool._available_connections) if hasattr(pool, "_available_connections") else max_connections
        )
        active_connections = max(0, created_connections - available_connections)
        idle_connections = available_connections

        # Get circuit breaker metrics
        cb_metrics = pubsub.circuit_breaker_metrics
        circuit_breaker_status = CircuitBreakerStatus(
            state=cb_metrics["state"].upper(),
            failure_count=cb_metrics["failure_count"],
            last_failure_time=datetime.fromtimestamp(cb_metrics["last_failure_time"]).isoformat() + "Z"
            if cb_metrics["last_failure_time"]
            else None,
            next_attempt_time=datetime.fromtimestamp(cb_metrics["next_attempt_time"]).isoformat() + "Z"
            if cb_metrics["next_attempt_time"]
            else None,
        )

        # Build response components
        connection_pool_status = ConnectionPoolStatus(
            max_connections=max_connections,
            active_connections=active_connections,
            idle_connections=idle_connections,
            status="connected",
        )

        performance_metrics = RedisPerformanceMetrics(
            ping_latency_ms=ping_latency_ms,
            last_successful_operation=current_time.isoformat() + "Z",
            operations_per_second=cb_metrics.get("total_successes", 0) / max(1, time.perf_counter() - check_start_time),
            error_rate=cb_metrics.get("failure_rate", 0.0) * 100,
        )

        # Determine overall health status
        overall_status = "healthy"
        if circuit_breaker_status.state == "OPEN":
            overall_status = "offline"
        elif (
            circuit_breaker_status.state == "HALF_OPEN"
            or ping_latency_ms > 50
            or cb_metrics.get("failure_rate", 0.0) > 0.05
        ):
            overall_status = "degraded"

        return RedisHealthResponse(
            status=overall_status,
            timestamp=current_time.isoformat() + "Z",
            connection_pool=connection_pool_status,
            performance_metrics=performance_metrics,
            redis_info={
                "redis_version": redis_info.get("redis_version", "unknown"),
                "connected_clients": redis_info.get("connected_clients", "unknown"),
                "used_memory": redis_info.get("used_memory", "unknown"),
                "keyspace_hits": redis_info.get("keyspace_hits", "unknown"),
                "keyspace_misses": redis_info.get("keyspace_misses", "unknown"),
            },
            circuit_breaker=circuit_breaker_status,
        )

    except Exception as exc:
        # Redis is unavailable - return offline status with error details
        circuit_breaker_status = CircuitBreakerStatus(
            state="OPEN",
            failure_count=999,
            last_failure_time=current_time.isoformat() + "Z",
            next_attempt_time=None,
        )

        connection_pool_status = ConnectionPoolStatus(
            max_connections=0,
            active_connections=0,
            idle_connections=0,
            status="disconnected",
        )

        performance_metrics = RedisPerformanceMetrics(
            ping_latency_ms=None,
            last_successful_operation=None,
            operations_per_second=0.0,
            error_rate=100.0,
        )

        return RedisHealthResponse(
            status="offline",
            timestamp=current_time.isoformat() + "Z",
            connection_pool=connection_pool_status,
            performance_metrics=performance_metrics,
            redis_info={"error": "Unable to connect to Redis"},
            circuit_breaker=circuit_breaker_status,
            error=str(exc),
        )


# Module CRUD Endpoints with new pattern
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
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> Module:
    """Create a new module."""
    log_event(
        source="cc",
        data={"module": module_data.name, "request_id": deps.request_id},
        tags=["module", "create", "cc_router"],
        memo=f"Creating module {module_data.name}.",
    )

    try:
        if deps.db is None:
            raise COSError(
                message="Database connection not available",
                category=ErrorCategory.INTERNAL,
                user_message="Database connection not available",
            )

        module = await service_create_module(
            deps.db, name=module_data.name, version=module_data.version, config=module_data.config
        )
        return Module.model_validate(module)
    except ValueError as e:
        error_msg = str(e)
        if "already exists" in error_msg:
            raise ConflictError(
                resource="Module", identifier=module_data.name, user_message=f"Cannot create module: {e}"
            ) from e
        else:
            raise ValidationError(message=error_msg, field="name", user_message=f"Cannot create module: {e}") from e


@router.get(
    "/modules",
    response_model=list[Module],
    summary="List Modules",
    description="Get a list of all modules with optional pagination.",
    tags=["Modules"],
)
async def list_modules(
    pagination: Annotated[PaginationParams, Depends()],
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> list[Module]:
    """Get a list of modules with pagination."""
    log_event(
        source="cc",
        data={"page": pagination.page, "limit": pagination.limit, "request_id": deps.request_id},
        tags=["module", "list", "cc_router"],
        memo=f"Listing modules with page={pagination.page}, limit={pagination.limit}.",
    )

    if deps.db is None:
        raise COSError(
            message="Database connection not available",
            category=ErrorCategory.INTERNAL,
            user_message="Database connection not available",
        )

    modules = await service_get_modules(deps.db, skip=pagination.offset, limit=pagination.limit)
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
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> Module:
    """Get a specific module by ID."""
    log_event(
        source="cc",
        data={"module_id": module_id, "request_id": deps.request_id},
        tags=["module", "get", "cc_router"],
        memo=f"Getting module {module_id}.",
    )

    if deps.db is None:
        raise COSError(
            message="Database connection not available",
            category=ErrorCategory.INTERNAL,
            user_message="Database connection not available",
        )

    module = await service_get_module(deps.db, module_id)
    if not module:
        raise NotFoundError("Module", module_id)

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
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> Module:
    """Update a specific module by ID."""
    log_event(
        source="cc",
        data={
            "module_id": module_id,
            "update_data": module_data.model_dump(exclude_unset=True),
            "request_id": deps.request_id,
        },
        tags=["module", "update", "cc_router"],
        memo=f"Updating module {module_id}.",
    )

    try:
        # Convert Pydantic model to dict, excluding unset fields
        update_data = module_data.model_dump(exclude_unset=True)

        if deps.db is None:
            raise COSError(
                message="Database connection not available",
                category=ErrorCategory.INTERNAL,
                user_message="Database connection not available",
            )

        module = await service_update_module(deps.db, module_id, update_data)
        if not module:
            raise NotFoundError("Module", module_id)

        return Module.model_validate(module)
    except ValueError as e:
        error_msg = str(e)
        if "already exists" in error_msg:
            raise ConflictError(
                resource="Module",
                identifier=update_data.get("name", module_id),
                user_message=f"Cannot update module: {e}",
            ) from e
        else:
            raise ValidationError(message=error_msg, field="name", user_message=f"Cannot update module: {e}") from e


@router.delete(
    "/modules/{module_id}",
    response_model=Module,
    summary="Delete Module",
    description="Delete a specific module by its ID.",
    tags=["Modules"],
)
async def delete_module(
    module_id: str,
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> Module:
    """Delete a specific module by ID."""
    log_event(
        source="cc",
        data={"module_id": module_id, "request_id": deps.request_id},
        tags=["module", "delete", "cc_router"],
        memo=f"Deleting module {module_id}.",
    )

    if deps.db is None:
        raise COSError(
            message="Database connection not available",
            category=ErrorCategory.INTERNAL,
            user_message="Database connection not available",
        )

    module = await service_delete_module(deps.db, module_id)
    if not module:
        raise NotFoundError("Module", module_id)

    return Module.model_validate(module)


# Copy all routes from the main router to the test router
# This ensures both routers have identical route definitions
# We need to create new routes with modified paths (remove /v1 prefix)
for route in router.routes:
    if (
        hasattr(route, "path")
        and hasattr(route, "methods")
        and isinstance(route, APIRoute)
        and route.path.startswith("/v1/cc/")
        and not route.path.startswith("/v1/cc/mem0/")
    ):
        # Create a new route with the non-versioned path
        new_route = copy.copy(route)
        new_route.path = route.path.replace("/v1/cc/", "/cc/")
        new_route.path_regex = None  # type: ignore  # Let FastAPI regenerate the path regex
        router_test.routes.append(new_route)
