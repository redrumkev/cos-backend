"""API router for mem0 scratch data operations.

Provides REST endpoints for scratch data management with proper
FastAPI patterns, error handling, and background task integration.

Reference implementation for future module API patterns.
"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from . import mem0_service
from .deps import get_cc_db
from .schemas import CleanupResponse, ScratchNoteCreate, ScratchNoteResponse, ScratchNoteUpdate, ScratchStatsResponse

router = APIRouter(prefix="/scratch", tags=["scratch"])


@router.post("/notes", response_model=ScratchNoteResponse)
async def create_note(
    data: ScratchNoteCreate, 
    db: AsyncSession = Depends(get_cc_db)  # noqa: B008
) -> ScratchNoteResponse:
    """Create a scratch note with optional TTL."""
    try:
        note = await mem0_service.create_note(db, data.key, data.content, data.ttl_days)
        return ScratchNoteResponse.model_validate(note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create note: {e!s}") from e


@router.get("/notes/{note_id}", response_model=ScratchNoteResponse)
async def get_note(
    note_id: int, 
    db: AsyncSession = Depends(get_cc_db)  # noqa: B008
) -> ScratchNoteResponse:
    """Get a scratch note by ID."""
    note = await mem0_service.get_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return ScratchNoteResponse.model_validate(note)


@router.get("/notes/key/{key}", response_model=ScratchNoteResponse)
async def get_note_by_key(
    key: str, 
    db: AsyncSession = Depends(get_cc_db)  # noqa: B008
) -> ScratchNoteResponse:
    """Get a scratch note by key."""
    note = await mem0_service.get_note_by_key(db, key)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return ScratchNoteResponse.model_validate(note)


@router.get("/notes", response_model=list[ScratchNoteResponse])
async def list_notes(
    db: AsyncSession = Depends(get_cc_db),  # noqa: B008
    key_prefix: str | None = Query(None, description="Filter by key prefix"),
    include_expired: bool = Query(False, description="Include expired notes"),
    limit: int = Query(100, description="Maximum number of notes to return", ge=1, le=1000),
    offset: int = Query(0, description="Number of notes to skip", ge=0),
) -> list[ScratchNoteResponse]:
    """List scratch notes with filtering and pagination."""
    notes = await mem0_service.list_notes(db, key_prefix, include_expired, limit, offset)
    return [ScratchNoteResponse.model_validate(note) for note in notes]


@router.put("/notes/{note_id}", response_model=ScratchNoteResponse)
async def update_note(
    note_id: int, 
    data: ScratchNoteUpdate, 
    db: AsyncSession = Depends(get_cc_db)  # noqa: B008
) -> ScratchNoteResponse:
    """Update a scratch note's content and/or TTL."""
    note = await mem0_service.update_note(db, note_id, data.content, data.ttl_days)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return ScratchNoteResponse.model_validate(note)


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: int, 
    db: AsyncSession = Depends(get_cc_db)  # noqa: B008
) -> dict[str, Any]:
    """Delete a scratch note by ID."""
    deleted = await mem0_service.delete_note(db, note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"message": f"Note {note_id} deleted successfully"}


@router.get("/stats", response_model=ScratchStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_cc_db)  # noqa: B008
) -> ScratchStatsResponse:
    """Get comprehensive statistics about scratch notes."""
    stats = await mem0_service.get_stats(db)
    return ScratchStatsResponse.model_validate(stats)


@router.post("/cleanup", response_model=CleanupResponse)
async def trigger_cleanup(
    background_tasks: BackgroundTasks, 
    db: AsyncSession = Depends(get_cc_db)  # noqa: B008
) -> CleanupResponse:
    """Trigger cleanup manually and get immediate results."""
    # Run cleanup immediately and return results
    result = await mem0_service.run_cleanup(db)
    return CleanupResponse.model_validate(result)


@router.post("/cleanup/background")
async def trigger_cleanup_background(background_tasks: BackgroundTasks) -> dict[str, str]:
    """Trigger cleanup as a background task (fire and forget)."""
    from .background import periodic_cleanup

    background_tasks.add_task(periodic_cleanup)
    return {"message": "Cleanup scheduled in background"}


@router.post("/stats/background")
async def collect_stats_background(background_tasks: BackgroundTasks) -> dict[str, str]:
    """Collect stats as a background task (fire and forget)."""
    from .background import get_scratch_stats

    background_tasks.add_task(get_scratch_stats)
    return {"message": "Stats collection scheduled in background"}
