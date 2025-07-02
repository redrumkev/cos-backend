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
from fastapi import FastAPI  # noqa: E402

from src.backend.cc.router import router  # noqa: E402
from src.common.logger import log_event  # noqa: E402
from src.graph.router import router as graph_router  # noqa: E402

# Create the FastAPI application instance
app: FastAPI = FastAPI(
    title="COS Backend",
    description="Control and Orchestration System API",
    version="0.1.0",
)

# Mount the CC router
app.include_router(router, prefix="/cc")

# Mount the graph router
app.include_router(graph_router, prefix="/graph")

# Log startup event
if os.getenv("RUN_INTEGRATION", "1") == "1":
    log_event(source="cos_main", data={"event": "startup"}, memo="COS FastAPI initialized.")
