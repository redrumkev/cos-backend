# MDC: app_entrypoint
# Add src/ to import path once
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add src/ to sys.path BEFORE any local imports
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Now import with consistent paths using src prefix
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from starlette.responses import Response  # noqa: E402

from src.backend.cc.router import router  # noqa: E402
from src.common.logger import log_event  # noqa: E402
from src.core_v2.patterns.error_handling import COSError  # noqa: E402
from src.core_v2.patterns.router import cos_error_handler, validation_error_handler  # noqa: E402
from src.graph.router import router as graph_router  # noqa: E402

# Create the FastAPI application instance
app: FastAPI = FastAPI(
    title="COS Backend",
    description="Control and Orchestration System API",
    version="0.1.0",
)


# Register global error handlers for the router pattern
# Create wrapper functions that match the exact signature expected by FastAPI
async def cos_error_handler_wrapper(request: Request, exc: Exception) -> Response:
    """Handle COSError exceptions."""
    if isinstance(exc, COSError):
        return await cos_error_handler(request, exc)
    raise exc


async def validation_error_handler_wrapper(request: Request, exc: Exception) -> Response:
    """Handle RequestValidationError exceptions."""
    if isinstance(exc, RequestValidationError):
        return await validation_error_handler(request, exc)
    raise exc


app.add_exception_handler(COSError, cos_error_handler_wrapper)
app.add_exception_handler(RequestValidationError, validation_error_handler_wrapper)

# Mount the CC router (router already has prefix configured)
app.include_router(router)

# Mount the graph router (router already has prefix configured)
app.include_router(graph_router)

# Log startup event
if os.getenv("RUN_INTEGRATION", "1") == "1":
    log_event(source="cos_main", data={"event": "startup"}, memo="COS FastAPI initialized.")
