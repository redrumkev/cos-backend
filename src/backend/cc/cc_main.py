"""Control Center module main entry point.

This file contains the FastAPI app initialization and router mounting for the CC module.
It serves as the entry point for the module when imported by the main application.
"""

# MDC: cc_module
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, Request, WebSocket

from src.common.logger import log_event
from src.common.request_id_middleware import RequestIDMiddleware
from src.graph.base import close_neo4j_connections
from src.graph.router import router as graph_router
from src.graph.router import router_test as graph_router_test

from .router import router, router_test

# Initialize logging for this module
logger = logging.getLogger(__name__)

# Global variable for logfire module
logfire_module: Any | None = None

# Import logfire with graceful degradation
try:
    import logfire

    _LOGFIRE_AVAILABLE = True
    logfire_module = logfire
except ImportError:
    logger.warning("Logfire package not available. FastAPI auto-instrumentation will be disabled.")
    _LOGFIRE_AVAILABLE = False


def _initialize_logfire() -> bool:
    """Initialize Logfire SDK with token from environment.

    Returns
    -------
        bool: True if successful, False otherwise.

    """
    if not _LOGFIRE_AVAILABLE or logfire_module is None:
        logger.info("Logfire not available, skipping initialization")
        return False

    token = os.environ.get("LOGFIRE_TOKEN")
    if not token:
        logger.info("LOGFIRE_TOKEN not found in environment. Auto-instrumentation disabled.")
        return False

    try:
        logfire_module.configure(service_name="cos-cc")
        logger.info("Logfire initialized successfully for FastAPI auto-instrumentation")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Logfire: {e}")
        return False


def _request_attributes_mapper(request: Request | WebSocket, attributes: dict[str, Any]) -> dict[str, Any] | None:
    """Map request attributes for Logfire instrumentation.

    Args:
    ----
        request: The FastAPI request or websocket object
        attributes: Existing attributes dictionary

    Returns:
    -------
        Optional[dict[str, Any]]: Updated attributes dictionary or None

    """
    if isinstance(request, WebSocket):
        return attributes

    return {
        **attributes,
        "user_agent": request.headers.get("user-agent", "unknown"),
        # tests expect “client_ip”
        "client_ip": getattr(request.client, "host", "unknown") if request.client else "unknown",
    }


def _instrument_fastapi_app(app: FastAPI) -> bool:
    """Apply Logfire auto-instrumentation to FastAPI app.

    Args:
    ----
        app: The FastAPI application instance to instrument

    Returns:
    -------
        bool: True if instrumentation was applied, False otherwise.

    """
    if not _LOGFIRE_AVAILABLE or logfire_module is None:
        # tests expect to see this under INFO in the lifespan test
        logger.info("Logfire not available, skipping FastAPI instrumentation")
        return False

    try:
        # Configure Logfire for this FastAPI app with standard patterns
        logfire_module.instrument_fastapi(
            app,
            excluded_urls=["/health", "/docs", "/openapi.json", "/redoc"],
            request_attributes_mapper=_request_attributes_mapper,
        )
        logger.info("FastAPI auto-instrumentation applied successfully")
        return True
    except Exception as e:
        # match the tests expected error message
        logger.error(f"Failed to instrument FastAPI application: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for the CC module.

    Args:
    ----
        app: The FastAPI application instance

    Yields:
    ------
        None

    """
    # Startup tasks
    log_event(
        source="cc",
        data={"status": "starting"},
        tags=["lifecycle", "startup"],
        memo="Control Center module starting",
    )

    # Initialize Logfire and instrument FastAPI app
    logfire_initialized = _initialize_logfire()
    instrumentation_applied = False
    if logfire_initialized:
        instrumentation_applied = _instrument_fastapi_app(app)

    log_event(
        source="cc",
        data={
            "status": "started",
            "logfire_initialized": logfire_initialized,
            "instrumentation_applied": instrumentation_applied,
        },
        tags=["lifecycle", "startup", "instrumentation"],
        memo="Control Center module startup complete with instrumentation status",
    )

    yield

    # Shutdown tasks
    log_event(
        source="cc",
        data={"status": "stopping"},
        tags=["lifecycle", "shutdown"],
        memo="Control Center module shutting down",
    )

    # Close Neo4j connections
    await close_neo4j_connections()


# Create FastAPI app for the module
cc_app = FastAPI(
    title="Control Center API",
    description="Central coordination module for the Creative Operating System",
    version="0.1.0",
    lifespan=lifespan,
)

# Add middleware in proper order: RequestID first, then Logfire instrumentation happens in lifespan
cc_app.add_middleware(RequestIDMiddleware)

# Include the routers (use non-versioned routers for testing)
cc_app.include_router(router_test, tags=["cc"])
cc_app.include_router(graph_router_test, tags=["graph"])

# Entry router for use by main application (use versioned router)
cc_router = APIRouter()
cc_router.include_router(router, tags=["cc"])
cc_router.include_router(graph_router, tags=["graph"])
