# MDC: app_entrypoint
from fastapi import FastAPI

from backend.cc.router import router
from common.logger import log_event

# Create the FastAPI application instance
app: FastAPI = FastAPI(
    title="COS Backend",
    description="Control and Orchestration System API",
    version="0.1.0",
)

# Mount the CC router
app.include_router(router, prefix="/api/v1/cc")

# Log startup event
log_event(source="cos_main", data={"event": "startup"}, memo="COS FastAPI initialized.")
