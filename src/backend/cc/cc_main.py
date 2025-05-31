"""Control Center module main entry point.

This file contains the FastAPI app initialization and router mounting for the CC module.
It serves as the entry point for the module when imported by the main application.
"""

# MDC: cc_module
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from src.common.logger import log_event

from .router import router


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

    # Configure any module-specific startup tasks here

    yield

    # Shutdown tasks
    log_event(
        source="cc",
        data={"status": "stopping"},
        tags=["lifecycle", "shutdown"],
        memo="Control Center module shutting down",
    )


# Create FastAPI app for the module
cc_app = FastAPI(
    title="Control Center API",
    description="Central coordination module for the Creative Operating System",
    version="0.1.0",
    lifespan=lifespan,
)

# Include the router with prefix
cc_app.include_router(router, prefix="/cc", tags=["cc"])

# Entry router for use by main application
cc_router = APIRouter()
cc_router.include_router(router, prefix="/cc", tags=["cc"])
