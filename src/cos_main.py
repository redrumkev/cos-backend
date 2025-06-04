# MDC: app_entrypoint
# Add src/ to import path once
from __future__ import annotations

import sys
from pathlib import Path

from backend.cc.router import router
from common.logger import log_event
from fastapi import FastAPI
from graph.router import router as graph_router

src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

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
log_event(source="cos_main", data={"event": "startup"}, memo="COS FastAPI initialized.")
