"""Service layer for mem0 scratch data operations.

Provides business logic layer with configuration defaults, validation,
and integrated logging for scratch data management.

Reference implementation for future module service patterns.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.config import get_settings
from src.common.logger import log_event

from . import mem0_crud
from .mem0_models import ScratchNote


async def create_note(
    db: AsyncSession, key: str, content: str | None = None, ttl_days: int | None = None, use_default_ttl: bool = False
) -> ScratchNote:
    """Create scratch note with optional defaults from config."""
    # Only apply default TTL if explicitly requested
    if ttl_days is None and use_default_ttl:
        ttl_days = get_settings().SCRATCH_DEFAULT_TTL_DAYS

    # Validate key length
    if len(key) > 255:
        raise ValueError("Key cannot exceed 255 characters")

    log_event(
        source="cc_scratch",
        data={"key": key, "ttl_days": ttl_days, "has_content": content is not None},
        tags=["scratch", "create"],
        memo=f"Creating scratch note with key '{key}'",
    )

    return await mem0_crud.create_scratch_note(db, key, content, ttl_days)


async def get_note(db: AsyncSession, note_id: int) -> ScratchNote | None:
    """Get a scratch note by ID with logging."""
    note = await mem0_crud.get_scratch_note(db, note_id)

    log_event(
        source="cc_scratch",
        data={"note_id": note_id, "found": note is not None},
        tags=["scratch", "get"],
        memo=f"Retrieved scratch note {note_id}",
    )

    return note


async def get_note_by_key(db: AsyncSession, key: str) -> ScratchNote | None:
    """Get a scratch note by key with logging."""
    note = await mem0_crud.get_scratch_note_by_key(db, key)

    log_event(
        source="cc_scratch",
        data={"key": key, "found": note is not None},
        tags=["scratch", "get_by_key"],
        memo=f"Retrieved scratch note by key '{key}'",
    )

    return note


async def list_notes(
    db: AsyncSession, key_prefix: str | None = None, include_expired: bool = False, limit: int = 100, offset: int = 0
) -> list[ScratchNote]:
    """List scratch notes with validation and logging."""
    # Validate pagination
    if limit > 1000:
        limit = 1000  # Cap limit for performance
    if limit < 1:
        limit = 1
    if offset < 0:
        offset = 0

    notes = await mem0_crud.list_scratch_notes(db, key_prefix, include_expired, limit, offset)

    log_event(
        source="cc_scratch",
        data={
            "key_prefix": key_prefix,
            "include_expired": include_expired,
            "limit": limit,
            "offset": offset,
            "count": len(notes),
        },
        tags=["scratch", "list"],
        memo=f"Listed {len(notes)} scratch notes",
    )

    return notes


async def update_note(
    db: AsyncSession, note_id: int, content: str | None = None, ttl_days: int | None = None
) -> ScratchNote | None:
    """Update a scratch note with validation and logging."""
    note = await mem0_crud.update_scratch_note(db, note_id, content, ttl_days)

    log_event(
        source="cc_scratch",
        data={
            "note_id": note_id,
            "updated": note is not None,
            "updated_content": content is not None,
            "updated_ttl": ttl_days is not None,
        },
        tags=["scratch", "update"],
        memo=f"Updated scratch note {note_id}",
    )

    return note


async def delete_note(db: AsyncSession, note_id: int) -> bool:
    """Delete a scratch note with logging."""
    deleted = await mem0_crud.delete_scratch_note(db, note_id)

    log_event(
        source="cc_scratch",
        data={"note_id": note_id, "deleted": deleted},
        tags=["scratch", "delete"],
        memo=f"Deleted scratch note {note_id}",
    )

    return deleted


async def run_cleanup(db: AsyncSession) -> dict[str, Any]:
    """Run cleanup and return stats with comprehensive logging."""
    import time

    start_time = time.time()

    settings = get_settings()

    if not settings.SCRATCH_ENABLE_AUTO_CLEANUP:
        log_event(
            source="cc_scratch",
            data={"status": "disabled"},
            tags=["scratch", "cleanup"],
            memo="Cleanup disabled by configuration",
        )
        return {"status": "disabled", "deleted": 0, "execution_time_ms": 0}

    # Get stats before cleanup
    expired_count = await mem0_crud.get_expired_notes_count(db)
    total_count = await mem0_crud.count_scratch_notes(db, include_expired=True)

    batch_size = settings.SCRATCH_CLEANUP_BATCH_SIZE
    deleted = await mem0_crud.cleanup_expired_notes(db, batch_size)

    # Get stats after cleanup
    remaining_count = await mem0_crud.count_scratch_notes(db, include_expired=True)

    execution_time_ms = (time.time() - start_time) * 1000

    cleanup_stats = {
        "status": "completed",
        "deleted": deleted,
        "batch_size": batch_size,
        "expired_before": expired_count,
        "total_before": total_count,
        "remaining_after": remaining_count,
        "timestamp": datetime.now(UTC).isoformat(),
        "execution_time_ms": execution_time_ms,
    }

    log_event(
        source="cc_scratch",
        data=cleanup_stats,
        tags=["scratch", "cleanup"],
        memo=f"Cleanup completed, deleted {deleted} expired records",
    )

    return cleanup_stats


async def get_stats(db: AsyncSession) -> dict[str, Any]:
    """Get comprehensive statistics about scratch notes."""
    total_count = await mem0_crud.count_scratch_notes(db, include_expired=True)
    active_count = await mem0_crud.count_scratch_notes(db, include_expired=False)
    expired_count = await mem0_crud.get_expired_notes_count(db)

    stats = {
        "total_notes": total_count,
        "active_notes": active_count,
        "expired_notes": expired_count,
        "timestamp": datetime.now(UTC).isoformat(),
        "ttl_settings": {
            "default_ttl_days": get_settings().SCRATCH_DEFAULT_TTL_DAYS,
            "auto_cleanup_enabled": get_settings().SCRATCH_ENABLE_AUTO_CLEANUP,
            "cleanup_batch_size": get_settings().SCRATCH_CLEANUP_BATCH_SIZE,
        },
    }

    log_event(source="cc_scratch", data=stats, tags=["scratch", "stats"], memo="Generated scratch notes statistics")

    return stats
