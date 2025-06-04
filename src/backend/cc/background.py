"""Background task implementations for cc module.

Demonstrates background task patterns for async operations,
including cleanup tasks and proper resource management.

Reference implementation for future module background patterns.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from src.common.logger import log_event
from src.db.connection import get_async_db

from . import mem0_service


async def periodic_cleanup() -> dict[str, Any]:
    """Run periodic cleanup of expired scratch notes."""
    start_time = datetime.now(UTC)

    try:
        # Use the async generator properly
        async for db in get_async_db():
            try:
                result = await mem0_service.run_cleanup(db)

                # Add timing information
                end_time = datetime.now(UTC)
                result["duration_seconds"] = (end_time - start_time).total_seconds()
                result["started_at"] = start_time.isoformat()
                result["completed_at"] = end_time.isoformat()

                log_event(
                    source="cc_background",
                    data=result,
                    tags=["background", "cleanup", "success"],
                    memo="Background cleanup task completed successfully",
                )

                return result

            except Exception as e:
                error_result = {
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "started_at": start_time.isoformat(),
                    "failed_at": datetime.now(UTC).isoformat(),
                    "duration_seconds": (datetime.now(UTC) - start_time).total_seconds(),
                }

                log_event(
                    source="cc_background",
                    data=error_result,
                    tags=["background", "cleanup", "error"],
                    memo=f"Background cleanup task failed: {e!s}",
                )

                return error_result

            finally:
                # Session is automatically closed by the async generator
                pass

    except Exception as e:
        # Handle database connection errors
        error_result = {
            "status": "error",
            "error": f"Database connection failed: {e!s}",
            "error_type": type(e).__name__,
            "started_at": start_time.isoformat(),
            "failed_at": datetime.now(UTC).isoformat(),
            "duration_seconds": (datetime.now(UTC) - start_time).total_seconds(),
        }

        log_event(
            source="cc_background",
            data=error_result,
            tags=["background", "cleanup", "db_error"],
            memo=f"Background cleanup failed to connect to database: {e!s}",
        )

        return error_result

    # Fallback return (should never be reached due to async generator behavior)
    return {
        "status": "error",
        "error": "No database connection available",
        "error_type": "ConnectionError",
        "started_at": start_time.isoformat(),
        "failed_at": datetime.now(UTC).isoformat(),
        "duration_seconds": (datetime.now(UTC) - start_time).total_seconds(),
    }


async def get_scratch_stats() -> dict[str, Any]:
    """Background task to collect scratch statistics."""
    start_time = datetime.now(UTC)

    try:
        async for db in get_async_db():
            try:
                stats = await mem0_service.get_stats(db)

                # Add timing information
                end_time = datetime.now(UTC)
                stats["collection_duration_seconds"] = (end_time - start_time).total_seconds()
                stats["collection_started_at"] = start_time.isoformat()

                log_event(
                    source="cc_background",
                    data=stats,
                    tags=["background", "stats", "success"],
                    memo="Background stats collection completed successfully",
                )

                return stats

            except Exception as e:
                error_result = {
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "started_at": start_time.isoformat(),
                    "failed_at": datetime.now(UTC).isoformat(),
                    "duration_seconds": (datetime.now(UTC) - start_time).total_seconds(),
                }

                log_event(
                    source="cc_background",
                    data=error_result,
                    tags=["background", "stats", "error"],
                    memo=f"Background stats collection failed: {e!s}",
                )

                return error_result

    except Exception as e:
        # Handle database connection errors
        error_result = {
            "status": "error",
            "error": f"Database connection failed: {e!s}",
            "error_type": type(e).__name__,
            "started_at": start_time.isoformat(),
            "failed_at": datetime.now(UTC).isoformat(),
            "duration_seconds": (datetime.now(UTC) - start_time).total_seconds(),
        }

        log_event(
            source="cc_background",
            data=error_result,
            tags=["background", "stats", "db_error"],
            memo=f"Background stats collection failed to connect to database: {e!s}",
        )

        return error_result

    # Fallback return (should never be reached due to async generator behavior)
    return {
        "status": "error",
        "error": "No database connection available",
        "error_type": "ConnectionError",
        "started_at": start_time.isoformat(),
        "failed_at": datetime.now(UTC).isoformat(),
        "duration_seconds": (datetime.now(UTC) - start_time).total_seconds(),
    }


# FastAPI background task helpers
def create_cleanup_task() -> asyncio.Task[dict[str, Any]]:
    """Create background task for FastAPI cleanup."""
    return asyncio.create_task(periodic_cleanup())


def create_stats_task() -> asyncio.Task[dict[str, Any]]:
    """Create background task for FastAPI stats collection."""
    return asyncio.create_task(get_scratch_stats())


# Scheduled task runner (for future cron-like functionality)
async def run_scheduled_cleanup(interval_minutes: int = 60) -> None:
    """Run cleanup task on a schedule - for future scheduler integration."""
    log_event(
        source="cc_background",
        data={"interval_minutes": interval_minutes},
        tags=["background", "scheduler", "start"],
        memo=f"Starting scheduled cleanup with {interval_minutes} minute interval",
    )

    while True:
        try:
            await periodic_cleanup()
            await asyncio.sleep(interval_minutes * 60)  # Convert to seconds
        except asyncio.CancelledError:
            log_event(
                source="cc_background",
                data={},
                tags=["background", "scheduler", "cancelled"],
                memo="Scheduled cleanup task was cancelled",
            )
            break
        except Exception as e:
            log_event(
                source="cc_background",
                data={"error": str(e), "error_type": type(e).__name__},
                tags=["background", "scheduler", "error"],
                memo=f"Scheduled cleanup encountered error: {e!s}",
            )
            # Continue running despite errors
            await asyncio.sleep(60)  # Wait 1 minute before retrying
