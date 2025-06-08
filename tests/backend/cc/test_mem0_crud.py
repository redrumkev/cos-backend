"""Tests for mem0 CRUD operations.

Tests all CRUD functions including edge cases, error handling,
and cleanup operations.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest  # Phase 2: Remove for skip removal
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc import mem0_crud
from src.backend.cc.mem0_models import ScratchNote

# Phase 2: P2-MEM0-001 skip removed - implementing complete mem0 CRUD with PostgreSQL


@pytest.mark.asyncio
class TestMem0CRUD:
    """Test mem0 CRUD operations."""

    async def test_create_scratch_note_basic(self, db_session: AsyncSession) -> None:
        """Test basic scratch note creation."""
        note = await mem0_crud.create_scratch_note(db_session, key="test_key", content="test content")

        assert note.id is not None
        assert note.key == "test_key"
        assert note.content == "test content"
        assert note.expires_at is None
        assert note.created_at is not None

    async def test_create_scratch_note_with_ttl(self, db_session: AsyncSession) -> None:
        """Test scratch note creation with TTL."""
        ttl_days = 5
        note = await mem0_crud.create_scratch_note(db_session, key="ttl_key", content="ttl content", ttl_days=ttl_days)

        assert note.expires_at is not None
        # Ensure timezone-aware comparison
        expected_expiry = datetime.now(UTC) + timedelta(days=ttl_days)
        if note.expires_at.tzinfo is None:
            # If the database returns naive datetime, make comparison naive too
            expected_expiry = expected_expiry.replace(tzinfo=None)
        time_diff = abs((note.expires_at - expected_expiry).total_seconds())
        assert time_diff < 2  # Within 2 seconds

    async def test_get_scratch_note_by_id(self, db_session: AsyncSession) -> None:
        """Test retrieving scratch note by ID."""
        # Create a note first
        created_note = await mem0_crud.create_scratch_note(db_session, key="get_test", content="get content")

        # Retrieve it
        retrieved_note = await mem0_crud.get_scratch_note(db_session, created_note.id)

        assert retrieved_note is not None
        assert retrieved_note.id == created_note.id
        assert retrieved_note.key == "get_test"
        assert retrieved_note.content == "get content"

    async def test_get_scratch_note_nonexistent(self, db_session: AsyncSession) -> None:
        """Test retrieving non-existent scratch note."""
        note = await mem0_crud.get_scratch_note(db_session, 99999)
        assert note is None

    async def test_get_scratch_note_by_key(self, db_session: AsyncSession) -> None:
        """Test retrieving scratch note by key."""
        # Create a note first
        await mem0_crud.create_scratch_note(db_session, key="key_test", content="key content")

        # Retrieve it by key
        retrieved_note = await mem0_crud.get_scratch_note_by_key(db_session, "key_test")

        assert retrieved_note is not None
        assert retrieved_note.key == "key_test"
        assert retrieved_note.content == "key content"

    async def test_get_scratch_note_by_key_nonexistent(self, db_session: AsyncSession) -> None:
        """Test retrieving non-existent scratch note by key."""
        note = await mem0_crud.get_scratch_note_by_key(db_session, "nonexistent")
        assert note is None

    async def test_update_scratch_note(self, db_session: AsyncSession) -> None:
        """Test updating scratch note."""
        # Create a note first
        note = await mem0_crud.create_scratch_note(db_session, key="update_test", content="original")

        # Update it
        updated_note = await mem0_crud.update_scratch_note(db_session, note.id, content="updated content", ttl_days=3)

        assert updated_note is not None
        assert updated_note.content == "updated content"
        assert updated_note.expires_at is not None

    async def test_update_scratch_note_nonexistent(self, db_session: AsyncSession) -> None:
        """Test updating non-existent scratch note."""
        updated_note = await mem0_crud.update_scratch_note(db_session, 99999, content="new content")
        assert updated_note is None

    async def test_delete_scratch_note(self, db_session: AsyncSession) -> None:
        """Test deleting scratch note."""
        # Create a note first
        note = await mem0_crud.create_scratch_note(db_session, key="delete_test", content="to be deleted")

        # Delete it
        deleted = await mem0_crud.delete_scratch_note(db_session, note.id)
        assert deleted is True

        # Verify it's gone
        retrieved = await mem0_crud.get_scratch_note(db_session, note.id)
        assert retrieved is None

    async def test_delete_scratch_note_nonexistent(self, db_session: AsyncSession) -> None:
        """Test deleting non-existent scratch note."""
        deleted = await mem0_crud.delete_scratch_note(db_session, 99999)
        assert deleted is False

    async def test_list_scratch_notes_basic(self, db_session: AsyncSession) -> None:
        """Test listing scratch notes without filters."""
        # Create test notes
        await mem0_crud.create_scratch_note(db_session, key="list1", content="content1")
        await mem0_crud.create_scratch_note(db_session, key="list2", content="content2")

        # List them
        notes = await mem0_crud.list_scratch_notes(db_session)

        assert len(notes) >= 2
        keys = [note.key for note in notes]
        assert "list1" in keys
        assert "list2" in keys

    async def test_list_scratch_notes_with_key_prefix(self, db_session: AsyncSession) -> None:
        """Test listing scratch notes with key prefix filter."""
        # Create test notes
        await mem0_crud.create_scratch_note(db_session, key="prefix_test1", content="content1")
        await mem0_crud.create_scratch_note(db_session, key="prefix_test2", content="content2")
        await mem0_crud.create_scratch_note(db_session, key="other_key", content="content3")

        # List with prefix filter
        notes = await mem0_crud.list_scratch_notes(db_session, key_prefix="prefix_")

        assert len(notes) >= 2
        for note in notes:
            assert note.key.startswith("prefix_")

    async def test_list_scratch_notes_exclude_expired(self, db_session: AsyncSession) -> None:
        """Test listing scratch notes excluding expired ones."""
        current_time = datetime.now(UTC)

        # Create active note
        active_note = ScratchNote(key="active", content="active")
        active_note.expires_at = current_time + timedelta(days=1)
        db_session.add(active_note)

        # Create expired note
        expired_note = ScratchNote(key="expired", content="expired")
        expired_note.expires_at = current_time - timedelta(days=1)
        db_session.add(expired_note)

        await db_session.commit()

        # List excluding expired
        notes = await mem0_crud.list_scratch_notes(db_session, include_expired=False)

        keys = [note.key for note in notes]
        assert "active" in keys
        assert "expired" not in keys

    async def test_list_scratch_notes_include_expired(self, db_session: AsyncSession) -> None:
        """Test listing scratch notes including expired ones."""
        current_time = datetime.now(UTC)

        # Create expired note
        expired_note = ScratchNote(key="expired_include", content="expired")
        expired_note.expires_at = current_time - timedelta(days=1)
        db_session.add(expired_note)
        await db_session.commit()

        # List including expired
        notes = await mem0_crud.list_scratch_notes(db_session, include_expired=True)

        keys = [note.key for note in notes]
        assert "expired_include" in keys

    async def test_list_scratch_notes_pagination(self, db_session: AsyncSession) -> None:
        """Test pagination in listing scratch notes."""
        # Create multiple notes
        for i in range(5):
            await mem0_crud.create_scratch_note(db_session, key=f"page_test_{i}", content=f"content_{i}")

        # Test limit
        notes = await mem0_crud.list_scratch_notes(db_session, limit=2)
        assert len(notes) == 2

        # Test offset
        notes_offset = await mem0_crud.list_scratch_notes(db_session, limit=2, offset=2)
        assert len(notes_offset) == 2

        # Ensure different results
        first_keys = {note.key for note in notes}
        offset_keys = {note.key for note in notes_offset}
        assert first_keys != offset_keys

    async def test_cleanup_expired_notes(self, db_session: AsyncSession) -> None:
        """Test cleanup of expired notes."""
        current_time = datetime.now(UTC)

        # Create expired notes
        for i in range(3):
            expired_note = ScratchNote(key=f"cleanup_{i}", content="expired")
            expired_note.expires_at = current_time - timedelta(days=1)
            db_session.add(expired_note)

        # Create active note
        active_note = ScratchNote(key="active_cleanup", content="active")
        active_note.expires_at = current_time + timedelta(days=1)
        db_session.add(active_note)

        await db_session.commit()

        # Run cleanup
        deleted_count = await mem0_crud.cleanup_expired_notes(db_session, batch_size=10)

        assert deleted_count == 3

        # Verify active note still exists
        active_check = await mem0_crud.get_scratch_note_by_key(db_session, "active_cleanup")
        assert active_check is not None

    async def test_cleanup_expired_notes_batch_processing(self, db_session: AsyncSession) -> None:
        """Test cleanup with batch processing."""
        current_time = datetime.now(UTC)

        # Create 5 expired notes
        for i in range(5):
            expired_note = ScratchNote(key=f"batch_{i}", content="expired")
            expired_note.expires_at = current_time - timedelta(days=1)
            db_session.add(expired_note)

        await db_session.commit()

        # Run cleanup with small batch size - should only delete batch_size items
        deleted_count = await mem0_crud.cleanup_expired_notes(db_session, batch_size=2)

        # Should delete only 2 notes (the batch size)
        assert deleted_count == 2

        # Run again to delete remaining notes
        deleted_count_2 = await mem0_crud.cleanup_expired_notes(db_session, batch_size=2)
        assert deleted_count_2 == 2

        # Run final cleanup
        deleted_count_3 = await mem0_crud.cleanup_expired_notes(db_session, batch_size=2)
        assert deleted_count_3 == 1  # Last remaining note

    async def test_count_scratch_notes(self, db_session: AsyncSession) -> None:
        """Test counting scratch notes."""
        # Get initial count
        initial_count = await mem0_crud.count_scratch_notes(db_session)

        # Create test notes
        await mem0_crud.create_scratch_note(db_session, key="count1", content="content1")
        await mem0_crud.create_scratch_note(db_session, key="count2", content="content2")

        # Check count increased
        new_count = await mem0_crud.count_scratch_notes(db_session)
        assert new_count == initial_count + 2

    async def test_get_expired_notes_count(self, db_session: AsyncSession) -> None:
        """Test counting expired notes."""
        current_time = datetime.now(UTC)

        # Create expired notes
        for i in range(2):
            expired_note = ScratchNote(key=f"expired_count_{i}", content="expired")
            expired_note.expires_at = current_time - timedelta(days=1)
            db_session.add(expired_note)

        # Create active note
        active_note = ScratchNote(key="active_count", content="active")
        active_note.expires_at = current_time + timedelta(days=1)
        db_session.add(active_note)

        await db_session.commit()

        # Count expired notes
        expired_count = await mem0_crud.get_expired_notes_count(db_session)
        assert expired_count >= 2

    async def test_error_handling_database_error(self, db_session: AsyncSession) -> None:
        """Test error handling for database errors."""
        # Mock a database error during commit
        with (
            patch.object(db_session, "commit", side_effect=Exception("Database error")),
            pytest.raises(Exception, match="Database error"),
        ):
            await mem0_crud.create_scratch_note(db_session, key="error_test", content="test")

    async def test_transaction_rollback_on_error(self, db_session: AsyncSession) -> None:
        """Test that transactions are properly rolled back on errors."""
        # This test ensures that failed operations don't leave partial data
        initial_count = await mem0_crud.count_scratch_notes(db_session)

        # Try to create a note with invalid data (simulate error)
        with (
            patch.object(db_session, "commit", side_effect=Exception("Commit failed")),
            pytest.raises(Exception, match="Commit failed"),
        ):
            await mem0_crud.create_scratch_note(db_session, key="rollback_test", content="test")

        # The transaction should be automatically rolled back by SQLAlchemy
        # But we need to rollback explicitly in our test session
        await db_session.rollback()

        # Verify count hasn't changed
        final_count = await mem0_crud.count_scratch_notes(db_session)
        assert final_count == initial_count
