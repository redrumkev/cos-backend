"""CRUD operations for mem0 scratch data storage.

Demonstrates modern async SQLAlchemy 2.0 patterns with efficient queries,
proper transaction handling, and TTL cleanup operations.

Reference implementation for future module scratch storage patterns.
"""

from datetime import UTC, datetime

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .mem0_models import ScratchNote


async def create_scratch_note(
    db: AsyncSession, key: str, content: str | None = None, ttl_days: int | None = None
) -> ScratchNote:
    """Create a scratch note with optional TTL."""
    note = ScratchNote(key=key, content=content, ttl_days=ttl_days)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def get_scratch_note(db: AsyncSession, note_id: int) -> ScratchNote | None:
    """Get a scratch note by ID."""
    stmt = select(ScratchNote).where(ScratchNote.id == note_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_scratch_note_by_key(db: AsyncSession, key: str) -> ScratchNote | None:
    """Get a scratch note by key."""
    stmt = select(ScratchNote).where(ScratchNote.key == key)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_scratch_notes(
    db: AsyncSession, key_prefix: str | None = None, include_expired: bool = False, limit: int = 100, offset: int = 0
) -> list[ScratchNote]:
    """List scratch notes with filtering."""
    stmt = select(ScratchNote)

    if key_prefix:
        stmt = stmt.where(ScratchNote.key.startswith(key_prefix))

    if not include_expired:
        now = datetime.now(UTC)
        stmt = stmt.where(or_(ScratchNote.expires_at.is_(None), ScratchNote.expires_at > now))

    stmt = stmt.offset(offset).limit(limit).order_by(ScratchNote.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_scratch_note(
    db: AsyncSession, note_id: int, content: str | None = None, ttl_days: int | None = None
) -> ScratchNote | None:
    """Update a scratch note's content and/or TTL."""
    note = await get_scratch_note(db, note_id)
    if not note:
        return None

    if content is not None:
        note.content = content

    if ttl_days is not None:
        from datetime import timedelta

        note.expires_at = datetime.now(UTC) + timedelta(days=ttl_days)

    await db.commit()
    await db.refresh(note)
    return note


async def delete_scratch_note(db: AsyncSession, note_id: int) -> bool:
    """Delete a scratch note by ID. Returns True if deleted, False if not found."""
    note = await get_scratch_note(db, note_id)
    if not note:
        return False

    await db.delete(note)
    await db.commit()
    return True


async def cleanup_expired_notes(db: AsyncSession, batch_size: int = 1000) -> int:
    """Clean up expired notes in batches. Returns count of deleted records."""
    now = datetime.now(UTC)

    # Delete expired notes in batches for performance
    stmt = delete(ScratchNote).where(and_(ScratchNote.expires_at.is_not(None), ScratchNote.expires_at <= now))

    # For PostgreSQL, we can use LIMIT with DELETE
    # For SQLite, we need to handle differently
    if batch_size > 0:
        # First get IDs to delete
        select_stmt = (
            select(ScratchNote.id)
            .where(and_(ScratchNote.expires_at.is_not(None), ScratchNote.expires_at <= now))
            .limit(batch_size)
        )

        result = await db.execute(select_stmt)
        ids_to_delete = [row[0] for row in result.fetchall()]

        if not ids_to_delete:
            return 0

        # Delete by IDs
        delete_stmt = delete(ScratchNote).where(ScratchNote.id.in_(ids_to_delete))
        result = await db.execute(delete_stmt)
        deleted_count = result.rowcount
    else:
        # Delete all expired (no batch limit)
        result = await db.execute(stmt)
        deleted_count = result.rowcount

    await db.commit()
    return deleted_count


async def count_scratch_notes(db: AsyncSession, key_prefix: str | None = None, include_expired: bool = False) -> int:
    """Count scratch notes with optional filtering."""
    stmt = select(func.count(ScratchNote.id))

    if key_prefix:
        stmt = stmt.where(ScratchNote.key.startswith(key_prefix))

    if not include_expired:
        now = datetime.now(UTC)
        stmt = stmt.where(or_(ScratchNote.expires_at.is_(None), ScratchNote.expires_at > now))

    result = await db.execute(stmt)
    return result.scalar() or 0


async def get_expired_notes_count(db: AsyncSession) -> int:
    """Get count of expired notes for cleanup monitoring."""
    now = datetime.now(UTC)
    stmt = select(func.count(ScratchNote.id)).where(
        and_(ScratchNote.expires_at.is_not(None), ScratchNote.expires_at <= now)
    )
    result = await db.execute(stmt)
    return result.scalar() or 0
