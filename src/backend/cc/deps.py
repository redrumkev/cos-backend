"""FastAPI dependencies for the Control Center module.

This file contains shared dependencies that can be used across router endpoints
such as database sessions, authentication, and configuration access.
"""

# MDC: cc_module
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import log_event
from src.db.connection import get_async_db


async def get_module_config() -> dict[str, str]:
    """Get current CC module configuration for dependency injection.

    Returns:
        dict[str, str]: Module configuration

    """
    # Currently returning hardcoded config, will be replaced with actual config
    log_event(
        source="cc",
        data={},
        tags=["dependency", "config"],
        memo="Module configuration requested.",
    )
    return {
        "version": "0.1.0",
        "environment": "development",
    }


# Common type annotation for module config
ModuleConfig = Annotated[dict[str, str], Depends(get_module_config)]

# Remove the old get_db_session and its usage, update DBSession:
DBSession = Annotated[AsyncSession, Depends(get_async_db)]
