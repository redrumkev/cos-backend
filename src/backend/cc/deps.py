"""Dependencies for the **cc** module.

This module exposes `get_cc_db`, a FastAPI dependency that yields an `AsyncSession`
bound to the canonical asyncpg engine defined in `src.db.connection`.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import log_event
from src.db.connection import get_async_db

# Public dependency -----------------------------------------------------------


async def get_cc_db(
    db: AsyncSession = Depends(get_async_db),  # pragma: no cover  # noqa: B008
) -> AsyncSession:
    """Yield a real database session scoped to the current request / background task."""
    return db


# Back-compat alias (old tests may still import this name)
get_db_session = get_cc_db


async def get_module_config() -> dict[str, str]:
    """Get current CC module configuration for dependency injection.

    Returns
    -------
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


# Common type annotations
ModuleConfig = Annotated[dict[str, str], Depends(get_module_config)]

# DBSession type alias - proper implementation that FastAPI can handle
# This is a workaround for FastAPI not properly handling
# Annotated[AsyncSession, Depends(get_cc_db)] in all contexts
DBSession = Annotated[AsyncSession, Depends(get_cc_db)]
